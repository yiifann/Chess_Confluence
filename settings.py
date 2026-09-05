"""Shared presentation settings and canonical piece definitions."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

Game = Literal["chess", "xiangqi"]
Side = Literal["red", "black"]


@dataclass(frozen=True)
class PieceDefinition:
    """Canonical metadata shared by setup, rendering, and AI evaluation."""

    game: Game
    kind: str
    cost_units: int
    limit: int
    images: Mapping[Side, str]
    value_units: int


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
FPS = 60

BOARD_ORIGIN_X = 80
BOARD_ORIGIN_Y = 92
GRID_SIZE = 68
BOARD_COLS = 9
BOARD_ROWS = 10
PIECE_RADIUS = 25

SIDEBAR_X = 720
SIDEBAR_WIDTH = 520

UNITS_PER_POINT = 2
STARTING_BUDGET_UNITS = 80
MAX_BOUGHT_PIECES = 20
CHESS_KING_COST_UNITS = 6

# Economy values are integer half-point units: 1 unit is displayed as 0.5 points.


def format_points(units: int) -> str:
    """Format integer half-point units for player-facing text."""
    sign = "-" if units < 0 else ""
    whole_points, half_point = divmod(abs(units), UNITS_PER_POINT)
    suffix = "" if half_point == 0 else ".5"
    return f"{sign}{whole_points}{suffix}"


# Deployment zones are row indices from the top; Red therefore uses larger rows.
DEPLOYMENT_ROWS = {
    "red": {6, 7, 8, 9},
    "black": {0, 1, 2, 3},
}

TEAM_COLORS = {
    "red": (184, 48, 42),
    "black": (47, 52, 58),
}

COLORS = {
    "background": (238, 230, 210),
    "panel": (250, 247, 238),
    "board": (218, 176, 112),
    "board_dark": (85, 57, 38),
    "text": (43, 39, 35),
    "muted": (111, 103, 94),
    "accent": (42, 116, 103),
    "accent_hover": (53, 139, 123),
    "selected": (242, 190, 65),
    "move": (55, 151, 119),
    "capture": (202, 74, 64),
    "disabled": (189, 184, 173),
    "white": (255, 255, 255),
    "overlay": (24, 27, 31),
}

PIECE_DEFINITIONS: tuple[PieceDefinition, ...] = (
    PieceDefinition(
        "xiangqi",
        "bing",
        2,
        5,
        {"red": "Xiangqi_sl1.svg", "black": "Xiangqi_sd1.svg"},
        2,
    ),
    PieceDefinition(
        "xiangqi",
        "advisor",
        3,
        2,
        {"red": "Xiangqi_al1.svg", "black": "Xiangqi_ad1.svg"},
        3,
    ),
    PieceDefinition(
        "xiangqi",
        "elephant",
        4,
        2,
        {"red": "Xiangqi_el1.svg", "black": "Xiangqi_ed1.svg"},
        4,
    ),
    PieceDefinition(
        "xiangqi",
        "horse",
        5,
        2,
        {"red": "Xiangqi_hl1.svg", "black": "Xiangqi_hd1.svg"},
        5,
    ),
    PieceDefinition(
        "xiangqi",
        "cannon",
        9,
        2,
        {"red": "Xiangqi_cl1.svg", "black": "Xiangqi_cd1.svg"},
        9,
    ),
    PieceDefinition(
        "xiangqi",
        "rook",
        12,
        2,
        {"red": "Xiangqi_rl1.svg", "black": "Xiangqi_rd1.svg"},
        12,
    ),
    PieceDefinition(
        "chess",
        "pawn",
        2,
        8,
        {"red": "Chess_plt60.png", "black": "Chess_pdt60.png"},
        2,
    ),
    PieceDefinition(
        "chess",
        "knight",
        6,
        2,
        {"red": "Chess_nlt60.png", "black": "Chess_ndt60.png"},
        6,
    ),
    PieceDefinition(
        "chess",
        "bishop",
        7,
        2,
        {"red": "Chess_blt60.png", "black": "Chess_bdt60.png"},
        7,
    ),
    PieceDefinition(
        "chess",
        "rook",
        12,
        2,
        {"red": "Chess_rlt60.png", "black": "Chess_rdt60.png"},
        12,
    ),
    PieceDefinition(
        "chess",
        "queen",
        20,
        1,
        {"red": "Chess_qlt60.png", "black": "Chess_qdt60.png"},
        20,
    ),
    PieceDefinition(
        "xiangqi",
        "king",
        0,
        0,
        {"red": "Xiangqi_gl1.svg", "black": "Xiangqi_gd1.svg"},
        2000,
    ),
    PieceDefinition(
        "chess",
        "king",
        CHESS_KING_COST_UNITS,
        0,
        {"red": "Chess_klt60.png", "black": "Chess_kdt60.png"},
        2000,
    ),
)

PIECE_DEFINITION_BY_KEY: dict[tuple[Game, str], PieceDefinition] = {
    (definition.game, definition.kind): definition for definition in PIECE_DEFINITIONS
}
