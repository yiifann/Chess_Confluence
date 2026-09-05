"""Pygame-free match state, setup validation, and terminal adjudication."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pieces import (
    BoardPosition,
    Game,
    Piece,
    Side,
    legal_moves,
    valid_king_setup_position,
)
from settings import (
    BOARD_COLS,
    BOARD_ROWS,
    CHESS_KING_COST_UNITS,
    DEPLOYMENT_ROWS,
    MAX_BOUGHT_PIECES,
    PIECE_DEFINITION_BY_KEY,
    STARTING_BUDGET_UNITS,
    PieceDefinition,
)

TerminalReason = Literal[
    "king_capture",
    "no_legal_moves",
    "threefold_repetition",
    "move_limit",
    "resignation",
]
MatchPhase = Literal["setup", "playing", "game_over"]
SetupFailure = Literal[
    "insufficient_budget",
    "purchase_limit",
    "piece_limit",
    "invalid_position",
    "occupied",
    "not_owned",
    "king_fixed",
    "unknown_piece",
    "wrong_phase",
]
PROMOTION_OPTIONS = ("queen", "rook", "bishop", "knight")
NO_PROGRESS_PLY_LIMIT = 100


@dataclass(frozen=True)
class GameResult:
    """Terminal result; ``winner`` is ``None`` for a draw."""

    winner: Side | None
    reason: TerminalReason


@dataclass(frozen=True)
class SetupOutcome:
    """Result of one validated setup mutation."""

    accepted: bool
    failure: SetupFailure | None = None
    piece: Piece | None = None
    cost_units: int = 0


@dataclass(frozen=True)
class MoveOutcome:
    """Observable effects produced by one applied battle action."""

    piece: Piece
    captured: Piece | None
    promotion_required: bool
    result: GameResult | None


@dataclass
class GameState:
    """All mutable, renderer-independent state for one match."""

    pieces: list[Piece]
    kings: dict[Side, Piece]
    budget_units: dict[Side, int]
    purchase_counts: dict[tuple[Side, Game, str], int]
    bought_totals: dict[Side, int]
    next_piece_id: int
    phase: MatchPhase = "setup"
    turn: Side = "red"
    result: GameResult | None = None
    pending_promotion_id: int | None = None
    no_progress_plies: int = 0
    repetition_counts: dict[tuple[object, ...], int] = field(default_factory=dict)

    @classmethod
    def fresh(cls) -> GameState:
        red_king = Piece(1, "xiangqi", "king", "red", (4, 9))
        black_king = Piece(2, "xiangqi", "king", "black", (4, 0))
        return cls(
            pieces=[red_king, black_king],
            kings={"red": red_king, "black": black_king},
            budget_units={
                "red": STARTING_BUDGET_UNITS,
                "black": STARTING_BUDGET_UNITS,
            },
            purchase_counts={},
            bought_totals={"red": 0, "black": 0},
            next_piece_id=3,
        )


class IllegalAction(ValueError):
    """Raised when a caller asks the engine to apply an illegal battle action."""


class GameEngine:
    """Authoritative setup and battle rules independent of the Pygame UI."""

    def __init__(self) -> None:
        self.state = GameState.fresh()

    def reset(self) -> None:
        """Replace all match data with a fresh setup state."""
        self.state = GameState.fresh()

    def piece_at(self, position: BoardPosition) -> Piece | None:
        return next(
            (piece for piece in self.state.pieces if piece.position == position),
            None,
        )

    def pending_promotion(self) -> Piece | None:
        piece_id = self.state.pending_promotion_id
        if piece_id is None:
            return None
        return next(
            (piece for piece in self.state.pieces if piece.piece_id == piece_id),
            None,
        )

    def can_buy(self, side: Side, definition: PieceDefinition) -> bool:
        key = (side, definition.game, definition.kind)
        return (
            self.state.phase == "setup"
            and definition.limit > 0
            and self.state.budget_units[side] >= definition.cost_units
            and self.state.purchase_counts.get(key, 0) < definition.limit
            and self.state.bought_totals[side] < MAX_BOUGHT_PIECES
        )

    def set_king_type(self, side: Side, game: Game) -> SetupOutcome:
        """Change leader rules and charge or refund the chess-king premium."""
        if self.state.phase != "setup":
            return SetupOutcome(False, "wrong_phase")
        king = self.state.kings[side]
        if king.game == game:
            return SetupOutcome(True, piece=king)
        if game == "chess":
            if self.state.budget_units[side] < CHESS_KING_COST_UNITS:
                return SetupOutcome(False, "insufficient_budget")
            self.state.budget_units[side] -= CHESS_KING_COST_UNITS
        else:
            self.state.budget_units[side] += CHESS_KING_COST_UNITS
        king.game = game
        return SetupOutcome(True, piece=king, cost_units=CHESS_KING_COST_UNITS)

    def place_king(self, side: Side, position: BoardPosition) -> SetupOutcome:
        if self.state.phase != "setup":
            return SetupOutcome(False, "wrong_phase")
        king = self.state.kings[side]
        if not valid_king_setup_position(king, position):
            return SetupOutcome(False, "invalid_position")
        occupant = self.piece_at(position)
        if occupant is not None and occupant is not king:
            return SetupOutcome(False, "occupied")
        king.position = position
        return SetupOutcome(True, piece=king)

    def buy_piece(
        self,
        side: Side,
        definition: PieceDefinition,
        position: BoardPosition,
    ) -> SetupOutcome:
        """Validate and apply one shop purchase at a deployment position."""
        if self.state.phase != "setup":
            return SetupOutcome(False, "wrong_phase")
        canonical = PIECE_DEFINITION_BY_KEY.get((definition.game, definition.kind))
        if canonical is None or canonical != definition or canonical.limit <= 0:
            return SetupOutcome(False, "unknown_piece")
        definition = canonical
        if not self.can_buy(side, definition):
            key = (side, definition.game, definition.kind)
            failure: SetupFailure
            if self.state.budget_units[side] < definition.cost_units:
                failure = "insufficient_budget"
            elif self.state.purchase_counts.get(key, 0) >= definition.limit:
                failure = "purchase_limit"
            else:
                failure = "piece_limit"
            return SetupOutcome(False, failure)
        if (
            position[1] not in DEPLOYMENT_ROWS[side]
            or not 0 <= position[0] < BOARD_COLS
        ):
            return SetupOutcome(False, "invalid_position")
        if self.piece_at(position) is not None:
            return SetupOutcome(False, "occupied")

        piece = Piece(
            self.state.next_piece_id,
            definition.game,
            definition.kind,
            side,
            position,
        )
        self.state.next_piece_id += 1
        self.state.pieces.append(piece)
        self.state.budget_units[side] -= definition.cost_units
        key = (side, definition.game, definition.kind)
        self.state.purchase_counts[key] = self.state.purchase_counts.get(key, 0) + 1
        self.state.bought_totals[side] += 1
        return SetupOutcome(True, piece=piece, cost_units=definition.cost_units)

    def remove_setup_piece(
        self,
        side: Side,
        position: BoardPosition,
    ) -> SetupOutcome:
        """Remove a purchased piece and refund its full setup cost."""
        if self.state.phase != "setup":
            return SetupOutcome(False, "wrong_phase")
        piece = self.piece_at(position)
        if piece is None or piece.side != side:
            return SetupOutcome(False, "not_owned")
        if piece.kind == "king":
            return SetupOutcome(False, "king_fixed")
        definition = PIECE_DEFINITION_BY_KEY[(piece.game, piece.kind)]
        self.state.pieces.remove(piece)
        self.state.budget_units[side] += definition.cost_units
        key = (side, piece.game, piece.kind)
        self.state.purchase_counts[key] -= 1
        self.state.bought_totals[side] -= 1
        return SetupOutcome(True, piece=piece, cost_units=definition.cost_units)

    def setup_is_valid(self, side: Side) -> bool:
        king = self.state.kings[side]
        return valid_king_setup_position(king, king.position)

    def start_battle(self) -> GameResult | None:
        """Initialize turn history and adjudicate an immobile starting side."""
        if not self.setup_is_valid("red") or not self.setup_is_valid("black"):
            raise IllegalAction("both leaders need valid setup positions")
        self.state.turn = "red"
        self.state.phase = "playing"
        self.state.result = None
        self.state.pending_promotion_id = None
        self.state.no_progress_plies = 0
        self.state.repetition_counts = {}
        return self._adjudicate_turn_start()

    def adjudicate_current_turn(self) -> GameResult | None:
        """Apply terminal rules without changing the current position."""
        if self.state.result is not None:
            return self.state.result
        if self.state.phase != "playing":
            raise IllegalAction("the battle has not started")
        return self._adjudicate_turn_start(record_repetition=False)

    def apply_action(
        self,
        piece_id: int,
        target: BoardPosition,
        promotion: str | None = None,
    ) -> MoveOutcome:
        """Validate and apply a move, including capture and optional promotion."""
        if self.state.result is not None:
            raise IllegalAction("the match is already over")
        if self.state.phase != "playing":
            raise IllegalAction("the battle has not started")
        if self.state.pending_promotion_id is not None:
            raise IllegalAction("a promotion choice is pending")
        piece = next(
            (item for item in self.state.pieces if item.piece_id == piece_id),
            None,
        )
        if piece is None or piece.side != self.state.turn:
            raise IllegalAction("the selected piece cannot move this turn")
        if target not in legal_moves(piece, self.state.pieces):
            raise IllegalAction("the target is not legal for the selected piece")

        captured = self.piece_at(target)
        is_chess_pawn = piece.game == "chess" and piece.kind == "pawn"
        is_foot_soldier = is_chess_pawn or (
            piece.game == "xiangqi" and piece.kind == "bing"
        )
        final_row = 0 if piece.side == "red" else BOARD_ROWS - 1
        will_promote = is_chess_pawn and target[1] == final_row
        if (
            will_promote
            and promotion is not None
            and promotion not in PROMOTION_OPTIONS
        ):
            raise IllegalAction("unsupported promotion kind")

        if captured is not None:
            self.state.pieces.remove(captured)
        piece.position = target
        piece.moved = True

        if captured is not None and captured.kind == "king":
            self._set_result(GameResult(piece.side, "king_capture"))
            return MoveOutcome(piece, captured, False, self.state.result)

        if will_promote:
            if promotion is None:
                self.state.pending_promotion_id = piece.piece_id
                return MoveOutcome(piece, captured, True, None)
            piece.kind = promotion

        result = self._complete_turn(captured is not None, is_foot_soldier)
        return MoveOutcome(piece, captured, False, result)

    def complete_promotion(self, kind: str) -> MoveOutcome:
        """Finish a pending human promotion and advance the turn."""
        piece = self.pending_promotion()
        if piece is None:
            raise IllegalAction("no promotion is pending")
        if kind not in PROMOTION_OPTIONS:
            raise IllegalAction("unsupported promotion kind")
        piece.kind = kind
        self.state.pending_promotion_id = None
        result = self._complete_turn(capture_happened=False, pawn_moved=True)
        return MoveOutcome(piece, None, False, result)

    def resign(self, side: Side) -> GameResult:
        """End the match immediately with the opposing side as winner."""
        if self.state.phase != "playing":
            raise IllegalAction("the battle has not started")
        result = GameResult(_other_side(side), "resignation")
        self._set_result(result)
        return result

    def legal_moves_for(self, piece_id: int) -> tuple[BoardPosition, ...]:
        """Return legal destinations for a live piece in the current turn."""
        piece = next(
            (item for item in self.state.pieces if item.piece_id == piece_id),
            None,
        )
        if (
            self.state.phase != "playing"
            or piece is None
            or piece.side != self.state.turn
        ):
            return ()
        return tuple(legal_moves(piece, self.state.pieces))

    def is_in_check(self, side: Side) -> bool:
        """Report whether the leader can be captured on the opponent's next move."""
        king_position = self.state.kings[side].position
        return any(
            piece.side != side
            and king_position in legal_moves(piece, self.state.pieces)
            for piece in self.state.pieces
        )

    def _complete_turn(
        self,
        capture_happened: bool,
        pawn_moved: bool,
    ) -> GameResult | None:
        self.state.pending_promotion_id = None
        self.state.no_progress_plies = (
            0 if capture_happened or pawn_moved else self.state.no_progress_plies + 1
        )
        self.state.turn = _other_side(self.state.turn)
        return self._adjudicate_turn_start()

    def _adjudicate_turn_start(
        self,
        *,
        record_repetition: bool = True,
    ) -> GameResult | None:
        if not any(
            legal_moves(piece, self.state.pieces)
            for piece in self.state.pieces
            if piece.side == self.state.turn
        ):
            self._set_result(
                GameResult(
                    _other_side(self.state.turn),
                    "no_legal_moves",
                )
            )
            return self.state.result

        if record_repetition:
            key = self._position_key()
            count = self.state.repetition_counts.get(key, 0) + 1
            self.state.repetition_counts[key] = count
            if count >= 3:
                self._set_result(GameResult(None, "threefold_repetition"))
        if (
            self.state.result is None
            and self.state.no_progress_plies >= NO_PROGRESS_PLY_LIMIT
        ):
            self._set_result(GameResult(None, "move_limit"))
        return self.state.result

    def _set_result(self, result: GameResult) -> None:
        self.state.result = result
        self.state.phase = "game_over"

    def _position_key(self) -> tuple[object, ...]:
        pieces = tuple(
            sorted(
                (
                    piece.game,
                    piece.kind,
                    piece.side,
                    piece.position,
                    piece.moved
                    if piece.game == "chess" and piece.kind == "pawn"
                    else False,
                )
                for piece in self.state.pieces
            )
        )
        return self.state.turn, pieces


def _other_side(side: Side) -> Side:
    return "black" if side == "red" else "red"
