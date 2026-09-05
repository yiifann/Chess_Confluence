"""AI policy interfaces and the built-in heuristic opponent.

Policies receive immutable, renderer-independent data. An RL-backed policy can
therefore implement :class:`GamePolicy` without depending on Pygame or reaching
into the live ``HybridChessGame`` object.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal, Protocol

from pieces import BoardPosition, Game, Piece, Side, legal_moves
from settings import PIECE_DEFINITION_BY_KEY

Difficulty = Literal["easy", "medium", "hard"]


@dataclass(frozen=True)
class PieceView:
    """Serializable snapshot of one piece."""

    piece_id: int
    game: Game
    kind: str
    side: Side
    position: BoardPosition
    moved: bool

    @classmethod
    def from_piece(cls, piece: Piece) -> PieceView:
        return cls(
            piece.piece_id,
            piece.game,
            piece.kind,
            piece.side,
            piece.position,
            piece.moved,
        )


@dataclass(frozen=True)
class GameObservation:
    """Immutable information supplied to a policy for a battle decision."""

    turn: Side
    pieces: tuple[PieceView, ...]
    board_columns: int
    board_rows: int

    @classmethod
    def from_pieces(
        cls,
        turn: Side,
        pieces: list[Piece],
        board_columns: int,
        board_rows: int,
    ) -> GameObservation:
        return cls(
            turn,
            tuple(
                PieceView.from_piece(piece)
                for piece in sorted(pieces, key=lambda item: item.piece_id)
            ),
            board_columns,
            board_rows,
        )


@dataclass(frozen=True)
class MoveAction:
    """A policy-selected move from one piece to one board intersection."""

    piece_id: int
    target: BoardPosition


@dataclass(frozen=True)
class CatalogOption:
    """One purchasable option exposed to a setup policy."""

    game: Game
    kind: str
    cost_units: int
    limit: int


@dataclass(frozen=True)
class SetupRequest:
    """Rules and available resources for one side's secret setup."""

    side: Side
    budget_units: int
    max_pieces: int
    catalog: tuple[CatalogOption, ...]
    deployment_rows: tuple[int, ...]
    occupied: tuple[BoardPosition, ...]
    chess_king_cost_units: int
    board_columns: int
    board_rows: int


@dataclass(frozen=True)
class SetupPlacement:
    """One requested non-leader purchase and its deployment intersection."""

    game: Game
    kind: str
    position: BoardPosition


@dataclass(frozen=True)
class SetupPlan:
    """Complete policy proposal for one side's secret deployment."""

    king_game: Game
    king_position: BoardPosition
    placements: tuple[SetupPlacement, ...]


class GamePolicy(Protocol):
    """Interface shared by heuristic, search, remote, and RL policies."""

    def choose_setup(self, request: SetupRequest) -> SetupPlan:
        """Return a complete desired setup; the game validates it before use."""

    def choose_move(
        self,
        observation: GameObservation,
        legal_actions: tuple[MoveAction, ...],
    ) -> MoveAction | None:
        """Choose one supplied legal action, or ``None`` if none exist."""

    def choose_promotion(
        self,
        observation: GameObservation,
        pawn: PieceView,
        options: tuple[str, ...],
    ) -> str:
        """Choose the kind produced by a chess pawn promotion."""


def enumerate_legal_actions(
    observation: GameObservation,
    side: Side,
) -> tuple[MoveAction, ...]:
    """Build a deterministic action mask suitable for heuristic or RL policies."""
    pieces = _materialize(observation)
    actions = [
        MoveAction(piece.piece_id, target)
        for piece in pieces
        if piece.side == side
        for target in legal_moves(piece, pieces)
    ]
    return tuple(sorted(actions, key=lambda action: (action.piece_id, action.target)))


class HeuristicPolicy:
    """Configurable opponent ranging from random play to defensive one-ply play."""

    def __init__(
        self,
        seed: int | None = None,
        difficulty: Difficulty = "medium",
        setup_seed: int | None = None,
    ) -> None:
        if difficulty not in ("easy", "medium", "hard"):
            raise ValueError(f"unsupported AI difficulty: {difficulty}")
        self.random = random.Random(seed)
        self.setup_random = random.Random(seed if setup_seed is None else setup_seed)
        self.difficulty = difficulty

    def choose_setup(self, request: SetupRequest) -> SetupPlan:
        """Build a varied, budget-aware army and place it by tactical role."""
        use_chess_king = (
            request.budget_units >= request.chess_king_cost_units
            and self.setup_random.random() < 0.3
        )
        king_game: Game = "chess" if use_chess_king else "xiangqi"
        remaining_units = request.budget_units - (
            request.chess_king_cost_units if king_game == "chess" else 0
        )

        occupied = set(request.occupied)
        king_position = self._choose_king_position(request, king_game, occupied)
        occupied.add(king_position)

        option_by_key = {
            (option.game, option.kind): option for option in request.catalog
        }
        priorities: list[tuple[Game, str]] = [
            ("chess", "queen"),
            ("xiangqi", "rook"),
            ("chess", "rook"),
            ("xiangqi", "cannon"),
            ("chess", "bishop"),
            ("chess", "knight"),
            ("xiangqi", "horse"),
            ("chess", "pawn"),
            ("xiangqi", "bing"),
            ("xiangqi", "elephant"),
            ("xiangqi", "advisor"),
        ]
        if self.setup_random.random() < 0.2:
            priorities.remove(("chess", "queen"))

        selected: list[CatalogOption] = []
        counts: dict[tuple[Game, str], int] = {}
        for key in priorities:
            option = option_by_key.get(key)
            if option is None or option.cost_units > remaining_units:
                continue
            if len(selected) >= request.max_pieces:
                break
            selected.append(option)
            counts[key] = 1
            remaining_units -= option.cost_units

        # Spend small remainders without exceeding per-kind or total-piece limits.
        affordable = sorted(
            request.catalog,
            key=lambda option: (
                option.cost_units,
                -_piece_value_units(option.game, option.kind),
            ),
        )
        while len(selected) < request.max_pieces:
            option = next(
                (
                    candidate
                    for candidate in affordable
                    if candidate.cost_units <= remaining_units
                    and counts.get((candidate.game, candidate.kind), 0)
                    < candidate.limit
                ),
                None,
            )
            if option is None:
                break
            selected.append(option)
            key = (option.game, option.kind)
            counts[key] = counts.get(key, 0) + 1
            remaining_units -= option.cost_units

        placements: list[SetupPlacement] = []
        for option in selected:
            position = self._choose_piece_position(request, option, occupied)
            if position is None:
                break
            occupied.add(position)
            placements.append(SetupPlacement(option.game, option.kind, position))
        return SetupPlan(king_game, king_position, tuple(placements))

    def choose_move(
        self,
        observation: GameObservation,
        legal_actions: tuple[MoveAction, ...],
    ) -> MoveAction | None:
        """Return the highest-scoring legal move, randomizing exact ties."""
        if not legal_actions:
            return None
        if self.difficulty == "easy":
            return self.random.choice(legal_actions)
        scored = [
            (
                self._score_action(
                    observation,
                    action,
                    consider_replies=self.difficulty == "hard",
                ),
                action,
            )
            for action in legal_actions
        ]
        best_score = max(score for score, _ in scored)
        best_actions = [
            action for score, action in scored if abs(score - best_score) < 0.001
        ]
        return self.random.choice(best_actions)

    def choose_promotion(
        self,
        observation: GameObservation,
        pawn: PieceView,
        options: tuple[str, ...],
    ) -> str:
        del observation, pawn
        return "queen" if "queen" in options else options[0]

    def _choose_king_position(
        self,
        request: SetupRequest,
        king_game: Game,
        occupied: set[BoardPosition],
    ) -> BoardPosition:
        back_row = (
            min(request.deployment_rows)
            if request.side == "black"
            else max(request.deployment_rows)
        )
        columns = range(request.board_columns) if king_game == "chess" else range(3, 6)
        rows = (
            request.deployment_rows
            if king_game == "chess"
            else tuple(
                row
                for row in request.deployment_rows
                if row in (range(0, 3) if request.side == "black" else range(7, 10))
            )
        )
        positions = [
            (column, row)
            for row in rows
            for column in columns
            if (column, row) not in occupied
        ]
        return min(
            positions,
            key=lambda position: (
                abs(position[1] - back_row),
                abs(position[0] - (request.board_columns - 1) / 2),
                self.setup_random.random(),
            ),
        )

    def _choose_piece_position(
        self,
        request: SetupRequest,
        option: CatalogOption,
        occupied: set[BoardPosition],
    ) -> BoardPosition | None:
        back_row = (
            min(request.deployment_rows)
            if request.side == "black"
            else max(request.deployment_rows)
        )
        front_row = (
            max(request.deployment_rows)
            if request.side == "black"
            else min(request.deployment_rows)
        )
        preferred_row = (
            front_row
            if option.kind in {"pawn", "bing"}
            else back_row
            if option.kind in {"rook", "queen"}
            else (back_row + front_row) // 2
        )
        positions = [
            (column, row)
            for row in request.deployment_rows
            for column in range(request.board_columns)
            if (column, row) not in occupied
        ]
        if not positions:
            return None
        return min(
            positions,
            key=lambda position: (
                abs(position[1] - preferred_row),
                abs(position[0] - (request.board_columns - 1) / 2),
                self.setup_random.random(),
            ),
        )

    def _score_action(
        self,
        observation: GameObservation,
        action: MoveAction,
        *,
        consider_replies: bool,
    ) -> float:
        """Evaluate immediate tactics and, on hard, opposing one-ply replies."""
        pieces = _materialize(observation)
        moving_piece = next(
            piece for piece in pieces if piece.piece_id == action.piece_id
        )
        captured = next(
            (piece for piece in pieces if piece.position == action.target), None
        )
        enemy_king = next(
            piece
            for piece in pieces
            if piece.side != moving_piece.side and piece.kind == "king"
        )
        old_distance = _manhattan(moving_piece.position, enemy_king.position)

        if captured is not None:
            pieces.remove(captured)
        moving_piece.position = action.target
        moving_piece.moved = True

        # Tiny noise prevents identical armies from repeating the same tied line.
        score = self.random.uniform(-0.025, 0.025)
        if captured is not None:
            score += _piece_value_units(captured.game, captured.kind) * 6
            if captured.kind == "king":
                return score

        new_distance = _manhattan(moving_piece.position, enemy_king.position)
        score += (old_distance - new_distance) * 0.35
        score += len(legal_moves(moving_piece, pieces)) * 0.04
        score += _forward_progress(moving_piece, observation.board_rows) * 0.03

        final_row = 0 if moving_piece.side == "red" else observation.board_rows - 1
        if (
            moving_piece.game == "chess"
            and moving_piece.kind == "pawn"
            and moving_piece.position[1] == final_row
        ):
            score += 8

        if not consider_replies:
            return score

        own_king = next(
            piece
            for piece in pieces
            if piece.side == moving_piece.side and piece.kind == "king"
        )
        enemy_replies = [
            (piece, target)
            for piece in pieces
            if piece.side != moving_piece.side
            for target in legal_moves(piece, pieces)
        ]
        # Leader exposure dominates material because capture ends the game.
        if any(target == own_king.position for _, target in enemy_replies):
            score -= 500
        threatened_value = max(
            (
                _piece_value_units(victim.game, victim.kind)
                for attacker, target in enemy_replies
                for victim in pieces
                if victim.side == moving_piece.side
                and victim.position == target
                and attacker.side != victim.side
            ),
            default=0,
        )
        score -= threatened_value * 0.15
        return score


def _materialize(observation: GameObservation) -> list[Piece]:
    return [
        Piece(
            view.piece_id,
            view.game,
            view.kind,
            view.side,
            view.position,
            view.moved,
        )
        for view in observation.pieces
    ]


def _manhattan(first: BoardPosition, second: BoardPosition) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def _forward_progress(piece: Piece, board_rows: int) -> int:
    return (
        board_rows - 1 - piece.position[1] if piece.side == "red" else piece.position[1]
    )


def _piece_value_units(game: Game, kind: str) -> int:
    """Read integer half-point value from the canonical piece catalog."""
    return PIECE_DEFINITION_BY_KEY[(game, kind)].value_units
