"""Piece model and move generation for the two-rule-system board."""

from __future__ import annotations

from settings import BOARD_COLS, BOARD_ROWS
from dataclasses import dataclass
from typing import Literal, Iterable

Position_grid = tuple[int, int]

red_labels = {
    "king": "帅",
    "advisor": "仕",
    "elephant": "相",
    "horse": "马",
    "rook": "车",
    "cannon": "炮",
    "pawn": "兵",
}

black_labels = {
    "king": "将",
    "advisor": "士",
    "elephant": "象",
    "horse": "马",
    "rook": "车",
    "cannon": "炮",
    "pawn": "卒",
}

# piece_id: unit identifier for the piece (not being used)
# game: either 

@dataclass
class Piece:
    piece_id: int
    game: Literal["chess", "xiangqi", "other"]
    kind: str
    side: Literal["red", "black"]
    position: Position_grid
    # promotion: bool
    # movement: 
    moved: bool = False

    @property
    def enemy_side(self) -> str:
        return "black" if self.side == "red" else "red"

    def label(self) -> str:
        if self.game == "chess":
            return {
                "pawn": "P",
                "knight": "N",
                "bishop": "B",
                "rook": "R",
                "queen": "Q",
            }[self.kind]

        return (red_labels if self.side == "red" else black_labels)[self.kind]


def inside(position: Position_grid) -> bool:
    x, y = position
    return 0 <= x < BOARD_COLS and 0 <= y < BOARD_ROWS


def occupancy(pieces: Iterable[Piece]) -> dict[Position_grid, Piece]:
    return {piece.position: piece for piece in pieces}


def legal_moves(piece: Piece, pieces: Iterable[Piece]) -> list[Position_grid]:
    """Return geometric legal moves.

    This demo intentionally uses king capture instead of check/checkmate, so a
    move is not filtered for whether it exposes the moving side's king.
    """
    board = occupancy(pieces)
    if piece.game == "xiangqi":
        return _xiangqi_moves(piece, board)
    return _chess_moves(piece, board)


def _can_land(piece: Piece, position: Position_grid, board: dict[Position_grid, Piece]) -> bool:
    return inside(position) and (
        position not in board or board[position].side != piece.side
    )


def _sliding_moves(
    piece: Piece,
    board: dict[Position_grid, Piece],
    directions: Iterable[Position_grid],
) -> list[Position_grid]:
    moves: list[Position_grid] = []
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


def _xiangqi_moves(piece: Piece, board: dict[Position_grid, Piece]) -> list[Position_grid]:
    x, y = piece.position

    if piece.kind == "rook":
        return _sliding_moves(piece, board, ((1, 0), (-1, 0), (0, 1), (0, -1)))

    if piece.kind == "cannon":
        moves: list[Position_grid] = []
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
        candidates = (
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
            for (leg_x, leg_y), (dx, dy) in candidates
            if (x + leg_x, y + leg_y) not in board
            and _can_land(piece, (x + dx, y + dy), board)
        ]

    if piece.kind == "elephant":
        moves = []
        for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
            target = (x + dx, y + dy)
            eye = (x + dx // 2, y + dy // 2)
            own_side = target[1] >= 5 if piece.side == "red" else target[1] <= 4
            if own_side and eye not in board and _can_land(piece, target, board):
                moves.append(target)
        return moves

    if piece.kind == "advisor":
        palace_rows = range(7, 10) if piece.side == "red" else range(0, 3)
        return [
            target
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1))
            if (target := (x + dx, y + dy))[0] in range(3, 6)
            and target[1] in palace_rows
            and _can_land(piece, target, board)
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

    if piece.kind == "pawn":
        forward = -1 if piece.side == "red" else 1
        candidates = [(x, y + forward)]
        crossed_river = y <= 4 if piece.side == "red" else y >= 5
        if crossed_river:
            candidates.extend(((x - 1, y), (x + 1, y)))
        return [target for target in candidates if _can_land(piece, target, board)]

    return []


def _chess_moves(piece: Piece, board: dict[Position_grid, Piece]) -> list[Position_grid]:
    x, y = piece.position

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
        moves: list[Position_grid] = []
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
