"""Shared configuration for the Hybrid Chess demo."""

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

# Deployment zones are expressed as board row indices.
DEPLOYMENT_ROWS = {
    "red": {7, 8, 9},
    "black": {0, 1, 2},
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

PIECE_CATALOG = [
    {
        "game": "xiangqi",
        "kind": "pawn",
        "name": "中象·兵/卒",
        "short": "兵",
        "cost": 1,
        "limit": 5,
    },
    {
        "game": "xiangqi",
        "kind": "advisor",
        "name": "中象·仕/士",
        "short": "仕",
        "cost": 2,
        "limit": 2,
    },
    {
        "game": "xiangqi",
        "kind": "elephant",
        "name": "中象·相/象",
        "short": "相",
        "cost": 2,
        "limit": 2,
    },
    {
        "game": "xiangqi",
        "kind": "horse",
        "name": "中象·马",
        "short": "马",
        "cost": 3,
        "limit": 2,
    },
    {
        "game": "xiangqi",
        "kind": "cannon",
        "name": "中象·炮",
        "short": "炮",
        "cost": 4,
        "limit": 2,
    },
    {
        "game": "xiangqi",
        "kind": "rook",
        "name": "中象·车",
        "short": "车",
        "cost": 5,
        "limit": 2,
    },
    {
        "game": "chess",
        "kind": "pawn",
        "name": "国象·兵",
        "short": "P",
        "cost": 1,
        "limit": 8,
    },
    {
        "game": "chess",
        "kind": "knight",
        "name": "国象·马",
        "short": "N",
        "cost": 3,
        "limit": 2,
    },
    {
        "game": "chess",
        "kind": "bishop",
        "name": "国象·象",
        "short": "B",
        "cost": 3,
        "limit": 2,
    },
    {
        "game": "chess",
        "kind": "rook",
        "name": "国象·车",
        "short": "R",
        "cost": 5,
        "limit": 2,
    },
    {
        "game": "chess",
        "kind": "queen",
        "name": "国象·后",
        "short": "Q",
        "cost": 9,
        "limit": 1,
    },
]

