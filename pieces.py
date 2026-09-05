"""Piece model and move generation for the two-rule-system board."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from settings import BOARD_COLS, BOARD_ROWS, DEPLOYMENT_ROWS

BoardPosition = tuple[int, int]
Game = Literal["chess", "xiangqi"]
Side = Literal["red", "black"]

RED_LABELS = {
    "king": "帥",
    "advisor": "仕",
    "elephant": "相",
    "horse": "馬",
    "rook": "車",
    "cannon": "炮",
    "pawn": "兵",
    "bing": "兵",
}

BLACK_LABELS = {
    "king": "將",
    "advisor": "士",
    "elephant": "象",
    "horse": "馬",
    "rook": "車",
    "cannon": "砲",
    "pawn": "卒",
    "bing": "卒",
}


@dataclass
class Piece:
    """Mutable live piece using chess or Xiangqi movement rules.

    ``moved`` currently records whether a chess pawn has lost its initial
    two-step option.
    """

    piece_id: int
    game: Game
    kind: str
    side: Side
    position: BoardPosition
    moved: bool = False

    @property
    def enemy_side(self) -> Side:
        return "black" if self.side == "red" else "red"

    def label(self) -> str:
        if self.game == "chess":
            return {
                "pawn": "Pawn",
                "knight": "Knight",
                "bishop": "Bishop",
                "rook": "Rook",
                "queen": "Queen",
                "king": "King",
            }[self.kind]

        labels = RED_LABELS if self.side == "red" else BLACK_LABELS
        return labels[self.kind]


def inside(position: BoardPosition) -> bool:
    """Return whether an intersection lies on the 9×10 board."""
    x, y = position
    return 0 <= x < BOARD_COLS and 0 <= y < BOARD_ROWS


def occupancy(pieces: Iterable[Piece]) -> dict[BoardPosition, Piece]:
    """Index pieces by position for efficient movement generation."""
    return {piece.position: piece for piece in pieces}


def valid_king_setup_position(king: Piece, position: BoardPosition) -> bool:
    """Return whether a king may occupy a position during secret setup."""
    x, y = position
    if king.game == "chess":
        return 0 <= x < BOARD_COLS and y in DEPLOYMENT_ROWS[king.side]
    palace_rows = range(7, 10) if king.side == "red" else range(0, 3)
    return x in range(3, 6) and y in palace_rows


def legal_moves(piece: Piece, pieces: Iterable[Piece]) -> list[BoardPosition]:
    """Return geometric legal moves.

    This demo intentionally uses king capture instead of check/checkmate, so a
    move is not filtered for whether it exposes the moving side's king.
    """
    board = occupancy(pieces)
    if piece.game == "xiangqi":
        return _xiangqi_moves(piece, board)
    return _chess_moves(piece, board)


def _can_land(
    piece: Piece,
    position: BoardPosition,
    board: dict[BoardPosition, Piece],
) -> bool:
    return inside(position) and (
        position not in board or board[position].side != piece.side
    )


def _sliding_moves(
    piece: Piece,
    board: dict[BoardPosition, Piece],
    directions: Iterable[BoardPosition],
) -> list[BoardPosition]:
    moves: list[BoardPosition] = []
    x, y = piece.position
    for dx, dy in directions:
        step = 1
        while True:
            target = (x + dx * step, y + dy * step)
            if not inside(target):
                break
            occupant = board.get(target)
            if occupant is None:
                moves.append(target)
            else:
                if occupant.side != piece.side:
                    moves.append(target)
                break
            step += 1
    return moves


def _xiangqi_moves(
    piece: Piece,
    board: dict[BoardPosition, Piece],
) -> list[BoardPosition]:
    x, y = piece.position

    if piece.kind == "rook":
        return _sliding_moves(piece, board, ((1, 0), (-1, 0), (0, 1), (0, -1)))

    if piece.kind == "cannon":
        # Before a screen, empty intersections are ordinary moves. After exactly
        # one screen, only the first occupied intersection can be captured.
        moves: list[BoardPosition] = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            step = 1
            screen_found = False
            while True:
                target = (x + dx * step, y + dy * step)
                if not inside(target):
                    break
                occupant = board.get(target)
                if not screen_found:
                    if occupant is None:
                        moves.append(target)
                    else:
                        screen_found = True
                elif occupant is not None:
                    if occupant.side != piece.side:
                        moves.append(target)
                    break
                step += 1
        return moves

    if piece.kind == "horse":
        # Each destination records the adjacent "leg" that must remain empty.
        horse_patterns = (
            ((1, 0), (2, 1)),
            ((1, 0), (2, -1)),
            ((-1, 0), (-2, 1)),
            ((-1, 0), (-2, -1)),
            ((0, 1), (1, 2)),
            ((0, 1), (-1, 2)),
            ((0, -1), (1, -2)),
            ((0, -1), (-1, -2)),
        )
        return [
            (x + dx, y + dy)
            for (leg_x, leg_y), (dx, dy) in horse_patterns
            if (x + leg_x, y + leg_y) not in board
            and _can_land(piece, (x + dx, y + dy), board)
        ]

    if piece.kind == "elephant":
        # This variant permits crossing the river but preserves the blocked-eye
        # rule at the diagonal midpoint.
        moves = []
        for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
            target = (x + dx, y + dy)
            eye = (x + dx // 2, y + dy // 2)
            if eye not in board and _can_land(piece, target, board):
                moves.append(target)
        return moves

    if piece.kind == "advisor":
        return [
            target
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1))
            if _can_land(piece, target := (x + dx, y + dy), board)
        ]

    if piece.kind == "king":
        palace_rows = range(7, 10) if piece.side == "red" else range(0, 3)
        return [
            target
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if (target := (x + dx, y + dy))[0] in range(3, 6)
            and target[1] in palace_rows
            and _can_land(piece, target, board)
        ]

    if piece.kind == "bing":
        forward = -1 if piece.side == "red" else 1
        pawn_targets = [(x, y + forward)]
        # A soldier gains sideways movement after crossing, but never retreats.
        crossed_river = y <= 4 if piece.side == "red" else y >= 5
        if crossed_river:
            pawn_targets.extend(((x - 1, y), (x + 1, y)))
        return [target for target in pawn_targets if _can_land(piece, target, board)]

    return []


def _chess_moves(
    piece: Piece,
    board: dict[BoardPosition, Piece],
) -> list[BoardPosition]:
    x, y = piece.position

    if piece.kind == "king":
        return [
            target
            for dx, dy in (
                (-1, -1),
                (0, -1),
                (1, -1),
                (-1, 0),
                (1, 0),
                (-1, 1),
                (0, 1),
                (1, 1),
            )
            if _can_land(piece, target := (x + dx, y + dy), board)
        ]

    if piece.kind == "rook":
        return _sliding_moves(piece, board, ((1, 0), (-1, 0), (0, 1), (0, -1)))
    if piece.kind == "bishop":
        return _sliding_moves(piece, board, ((1, 1), (1, -1), (-1, 1), (-1, -1)))
    if piece.kind == "queen":
        return _sliding_moves(
            piece,
            board,
            (
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ),
        )
    if piece.kind == "knight":
        return [
            target
            for dx, dy in (
                (1, 2),
                (2, 1),
                (2, -1),
                (1, -2),
                (-1, -2),
                (-2, -1),
                (-2, 1),
                (-1, 2),
            )
            if _can_land(piece, target := (x + dx, y + dy), board)
        ]
    if piece.kind == "pawn":
        moves: list[BoardPosition] = []
        forward = -1 if piece.side == "red" else 1
        one_step = (x, y + forward)
        if inside(one_step) and one_step not in board:
            moves.append(one_step)
            two_step = (x, y + 2 * forward)
            if not piece.moved and inside(two_step) and two_step not in board:
                moves.append(two_step)
        for dx in (-1, 1):
            target = (x + dx, y + forward)
            if inside(target) and target in board and board[target].side != piece.side:
                moves.append(target)
        return moves
    return []
