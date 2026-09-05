"""Shared configuration for the Hybrid Chess demo."""

from typing import Literal, TypedDict

Game = Literal["chess", "xiangqi"]
Side = Literal["red", "black"]


class CatalogItem(TypedDict):
    """Schema shared by the setup shop, renderer, and AI setup request."""

    game: Game
    kind: str
    cost: float
    limit: int
    images: dict[Side, str]


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

STARTING_BUDGET = 40
MAX_BOUGHT_PIECES = 20
CHESS_KING_COST = 3

# Prices are expressed as floats because the balancing scale permits 0.5 points.

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

PIECE_CATALOG: list[CatalogItem] = [
    {
        "game": "xiangqi",
        "kind": "bing",
        "cost": 1,
        "limit": 5,
        "images": {"red": "Xiangqi_sl1.svg", "black": "Xiangqi_sd1.svg"},
    },
    {
        "game": "xiangqi",
        "kind": "advisor",
        "cost": 1.5,
        "limit": 2,
        "images": {"red": "Xiangqi_al1.svg", "black": "Xiangqi_ad1.svg"},
    },
    {
        "game": "xiangqi",
        "kind": "elephant",
        "cost": 2,
        "limit": 2,
        "images": {"red": "Xiangqi_el1.svg", "black": "Xiangqi_ed1.svg"},
    },
    {
        "game": "xiangqi",
        "kind": "horse",
        "cost": 2.5,
        "limit": 2,
        "images": {"red": "Xiangqi_hl1.svg", "black": "Xiangqi_hd1.svg"},
    },
    {
        "game": "xiangqi",
        "kind": "cannon",
        "cost": 4.5,
        "limit": 2,
        "images": {"red": "Xiangqi_cl1.svg", "black": "Xiangqi_cd1.svg"},
    },
    {
        "game": "xiangqi",
        "kind": "rook",
        "cost": 6.0,
        "limit": 2,
        "images": {"red": "Xiangqi_rl1.svg", "black": "Xiangqi_rd1.svg"},
    },
    {
        "game": "chess",
        "kind": "pawn",
        "cost": 1.0,
        "limit": 8,
        "images": {"red": "Chess_plt60.png", "black": "Chess_pdt60.png"},
    },
    {
        "game": "chess",
        "kind": "knight",
        "cost": 3.0,
        "limit": 2,
        "images": {"red": "Chess_nlt60.png", "black": "Chess_ndt60.png"},
    },
    {
        "game": "chess",
        "kind": "bishop",
        "cost": 3.5,
        "limit": 2,
        "images": {"red": "Chess_blt60.png", "black": "Chess_bdt60.png"},
    },
    {
        "game": "chess",
        "kind": "rook",
        "cost": 6.0,
        "limit": 2,
        "images": {"red": "Chess_rlt60.png", "black": "Chess_rdt60.png"},
    },
    {
        "game": "chess",
        "kind": "queen",
        "cost": 10.0,
        "limit": 1,
        "images": {"red": "Chess_qlt60.png", "black": "Chess_qdt60.png"},
    },
    {
        "game": "xiangqi",
        "kind": "king",
        "cost": 0,
        "limit": 0,
        "images": {"red": "Xiangqi_gl1.svg", "black": "Xiangqi_gd1.svg"},
    },
    {
        "game": "chess",
        "kind": "king",
        "cost": CHESS_KING_COST,
        "limit": 0,
        "images": {"red": "Chess_klt60.png", "black": "Chess_kdt60.png"},
    },
]
