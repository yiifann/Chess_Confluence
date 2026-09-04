"""Hybrid Chess Demo: Chinese chess meets international chess."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

try:
    import pygame
except ImportError:  # Friendly message when launched before dependencies exist.
    print("pygame is missing. Run: python -m pip install -r requirements.txt")
    raise SystemExit(1)

from i18n import LANGUAGE_LABELS, Language, translate
from pieces import BoardPosition, Game, Piece, Side, legal_moves
from settings import (
    BOARD_COLS,
    BOARD_ORIGIN_X,
    BOARD_ORIGIN_Y,
    BOARD_ROWS,
    COLORS,
    DEPLOYMENT_ROWS,
    FPS,
    GRID_SIZE,
    MAX_BOUGHT_PIECES,
    PIECE_CATALOG,
    PIECE_RADIUS,
    SIDEBAR_WIDTH,
    SIDEBAR_X,
    STARTING_BUDGET,
    TEAM_COLORS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    CatalogItem,
)

PixelPosition = tuple[int, int]
GameState = Literal["menu", "setup", "handoff", "playing", "game_over"]
HandoffTarget = Literal["black", "play"]
ImageKey = tuple[Game, str, Side]


def find_cjk_font() -> str | None:
    """Pick a commonly available CJK font on Windows, macOS, or Linux."""
    candidates = (
        "wenquanyimicrohei",
        "microsoftyahei",
        "microsoftjhenghei",
        "pingfangsc",
        "hiraginosansgb",
        "notosanscjksc",
        "sourcehansanscn",
        "simhei",
        "arialunicodems",
    )
    available = set(pygame.font.get_fonts())
    for name in candidates:
        if name in available:
            return pygame.font.match_font(name)
    return None


class HybridChessGame:
    def __init__(self) -> None:
        pygame.init()
        self.language: Language = "zh"
        pygame.display.set_caption(self.tr("window_title"))
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_path = find_cjk_font()
        self.fonts = {
            "tiny": pygame.font.Font(self.font_path, 15),
            "small": pygame.font.Font(self.font_path, 18),
            "body": pygame.font.Font(self.font_path, 22),
            "button": pygame.font.Font(self.font_path, 24),
            "piece": pygame.font.Font(self.font_path, 27),
            "subtitle": pygame.font.Font(self.font_path, 30),
            "title": pygame.font.Font(self.font_path, 48),
        }
        self.running = True
        self.state: GameState = "menu"
        self.load_images()
        self.reset_match()

    def load_images(self) -> None:
        """Load each game-specific piece image, leaving fallback drawing available."""
        self.images: dict[ImageKey, pygame.Surface] = {}
        assets_dir = Path(__file__).parent / "assets"
        for item in PIECE_CATALOG:
            for side in ("red", "black"):
                image_path = assets_dir / item["images"][side]
                try:
                    image = pygame.image.load(image_path).convert_alpha()
                except (FileNotFoundError, pygame.error):
                    continue
                self.images[(item["game"], item["kind"], side)] = image

    def is_checked(self, side: Side) -> bool:
        king_position = self.kings[side].position
        return any(
            piece.side != side and king_position in legal_moves(piece, self.pieces)
            for piece in self.pieces
        )

    def reset_match(self) -> None:
        self.pieces: list[Piece] = [
            Piece(1, "xiangqi", "king", "red", (4, 9)),
            Piece(2, "xiangqi", "king", "black", (4, 0)),
        ]
        self.kings: dict[Side, Piece] = {"red": self.pieces[0], "black": self.pieces[1]}
        self.next_piece_id = 3
        self.budgets: dict[Side, int] = {
            "red": STARTING_BUDGET,
            "black": STARTING_BUDGET,
        }
        self.purchase_counts: dict[tuple[Side, Game, str], int] = {}
        self.bought_totals: dict[Side, int] = {"red": 0, "black": 0}
        self.setup_side: Side = "red"
        self.selected_catalog_index: int | None = None
        self.selected_piece: Piece | None = None
        self.available_moves: list[BoardPosition] = []
        self.turn: Side = "red"
        self.winner: Side | None = None
        self.pending_promotion: Piece | None = None
        self.handoff_target: HandoffTarget = "black"
        self.status = self.tr("status.setup.red")

    # ---------- Main loop and events ----------

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == "menu":
                    self.running = False
                else:
                    self.state = "menu"
                    self.reset_match()
            return
        if event.type != pygame.MOUSEBUTTONDOWN:
            return

        if self.state == "menu":
            self.handle_menu_click(event.pos)
        elif self.state == "setup":
            self.handle_setup_click(event.pos, event.button)
        elif self.state == "handoff":
            self.handle_handoff_click(event.pos)
        elif self.state == "playing":
            self.handle_play_click(event.pos, event.button)
        elif self.state == "game_over":
            self.handle_game_over_click(event.pos)

    def handle_menu_click(self, position: PixelPosition) -> None:
        for language, rect in self.language_rects().items():
            if rect.collidepoint(position):
                self.language = language
                pygame.display.set_caption(self.tr("window_title"))
                return
        if self.menu_start_rect().collidepoint(position):
            self.reset_match()
            self.state = "setup"

    def handle_setup_click(self, position: PixelPosition, button: int) -> None:
        if button == 1:
            for index, rect in enumerate(self.catalog_rects()):
                if rect.collidepoint(position):
                    if self.can_buy(index):
                        self.selected_catalog_index = index
                        item = PIECE_CATALOG[index]
                        self.status = self.tr(
                            "status.catalog_selected",
                            piece=self.catalog_item_name(item),
                        )
                    else:
                        self.status = self.tr("status.buy_unavailable")
                    return
            if self.finish_setup_rect().collidepoint(position):
                self.finish_setup()
                return

        board_position = self.mouse_to_board(position)
        if board_position is None:
            return
        if button == 1:
            self.try_place_piece(board_position)
        elif button == 3:
            self.try_remove_piece(board_position)

    def handle_handoff_click(self, position: PixelPosition) -> None:
        if not self.handoff_button_rect().collidepoint(position):
            return
        if self.handoff_target == "black":
            self.setup_side = "black"
            self.selected_catalog_index = None
            self.status = self.tr("status.setup.black")
            self.state = "setup"
        else:
            self.turn = "red"
            self.status = self.tr("status.play_start")
            self.state = "playing"

    def handle_play_click(self, position: PixelPosition, button: int) -> None:
        if button != 1:
            return
        if self.pending_promotion is not None:
            for kind, rect in self.promotion_rects().items():
                if rect.collidepoint(position):
                    self.pending_promotion.kind = kind
                    self.pending_promotion = None
                    self.end_turn()
                    return
            return

        board_position = self.mouse_to_board(position)
        if board_position is None:
            return
        clicked_piece = self.piece_at(board_position)

        if self.selected_piece and board_position in self.available_moves:
            self.move_selected_piece(board_position)
            return
        if clicked_piece and clicked_piece.side == self.turn:
            self.selected_piece = clicked_piece
            self.available_moves = legal_moves(clicked_piece, self.pieces)
            self.status = self.tr(
                "status.piece_selected", piece=self.describe_piece(clicked_piece)
            )
            return
        self.selected_piece = None
        self.available_moves = []
        self.status = self.tr("status.no_piece")

    def handle_game_over_click(self, position: PixelPosition) -> None:
        restart, menu = self.game_over_rects()
        if restart.collidepoint(position):
            self.reset_match()
            self.state = "setup"
        elif menu.collidepoint(position):
            self.reset_match()
            self.state = "menu"

    # ---------- Setup logic ----------

    def can_buy(self, catalog_index: int) -> bool:
        item = PIECE_CATALOG[catalog_index]
        count_key = (self.setup_side, item["game"], item["kind"])
        return (
            self.budgets[self.setup_side] >= item["cost"]
            and self.purchase_counts.get(count_key, 0) < item["limit"]
            and self.bought_totals[self.setup_side] < MAX_BOUGHT_PIECES
        )

    def try_place_piece(self, position: BoardPosition) -> None:
        if self.selected_catalog_index is None:
            self.status = self.tr("status.choose_catalog")
            return
        if position[1] not in DEPLOYMENT_ROWS[self.setup_side]:
            self.status = self.tr("status.deployment_only")
            return
        if self.piece_at(position) is not None:
            self.status = self.tr("status.occupied")
            return
        if not self.can_buy(self.selected_catalog_index):
            self.status = self.tr("status.cannot_buy")
            self.selected_catalog_index = None
            return

        item = PIECE_CATALOG[self.selected_catalog_index]
        piece = Piece(
            self.next_piece_id,
            item["game"],
            item["kind"],
            self.setup_side,
            position,
        )
        self.next_piece_id += 1
        self.pieces.append(piece)
        self.budgets[self.setup_side] -= item["cost"]
        key = (self.setup_side, item["game"], item["kind"])
        self.purchase_counts[key] = self.purchase_counts.get(key, 0) + 1
        self.bought_totals[self.setup_side] += 1
        self.status = self.tr(
            "status.placed",
            piece=self.catalog_item_name(item),
            budget=self.budgets[self.setup_side],
        )
        if not self.can_buy(self.selected_catalog_index):
            self.selected_catalog_index = None

    def try_remove_piece(self, position: BoardPosition) -> None:
        piece = self.piece_at(position)
        if piece is None or piece.side != self.setup_side:
            self.status = self.tr("status.remove_hint")
            return
        if piece.kind == "king":
            self.status = self.tr("status.king_fixed")
            return
        item = self.catalog_item_for(piece)
        self.pieces.remove(piece)
        self.budgets[self.setup_side] += item["cost"]
        key = (piece.side, piece.game, piece.kind)
        self.purchase_counts[key] -= 1
        self.bought_totals[self.setup_side] -= 1
        self.status = self.tr(
            "status.removed",
            piece=self.catalog_item_name(item),
            cost=item["cost"],
        )

    def finish_setup(self) -> None:
        self.selected_catalog_index = None
        self.state = "handoff"
        if self.setup_side == "red":
            self.handoff_target = "black"
        else:
            self.handoff_target = "play"

    # ---------- Battle logic ----------

    def move_selected_piece(self, target: BoardPosition) -> None:
        piece = self.selected_piece
        if piece is None:
            return
        captured = self.piece_at(target)
        if captured is not None:
            self.pieces.remove(captured)
        piece.position = target
        piece.moved = True
        self.selected_piece = None
        self.available_moves = []

        if captured is not None and captured.kind == "king":
            self.winner = piece.side
            self.status = self.tr(
                "status.king_captured", side=self.side_name(piece.side)
            )
            self.state = "game_over"
            return

        final_row = 0 if piece.side == "red" else BOARD_ROWS - 1
        if piece.game == "chess" and piece.kind == "pawn" and target[1] == final_row:
            self.pending_promotion = piece
            self.status = self.tr("status.promote")
            return
        self.end_turn()

    def end_turn(self) -> None:
        self.turn = "black" if self.turn == "red" else "red"
        self.status = self.tr("status.turn", side=self.side_name(self.turn))

    # ---------- Lookup and coordinates ----------

    def piece_at(self, position: BoardPosition) -> Piece | None:
        return next(
            (piece for piece in self.pieces if piece.position == position), None
        )

    @staticmethod
    def catalog_item_for(piece: Piece) -> CatalogItem:
        return next(
            item
            for item in PIECE_CATALOG
            if item["game"] == piece.game and item["kind"] == piece.kind
        )

    def tr(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def side_name(self, side: Side) -> str:
        return self.tr(f"side.{side}")

    def catalog_item_name(self, item: CatalogItem) -> str:
        game_name = self.tr(f"game.{item['game']}")
        piece_name = self.tr(f"piece.{item['game']}.{item['kind']}")
        return f"{game_name} · {piece_name}"

    def describe_piece(self, piece: Piece) -> str:
        game_name = self.tr(f"game.{piece.game}")
        piece_name = self.tr(f"piece.{piece.game}.{piece.kind}")
        return f"{game_name} · {piece_name}"

    def board_to_pixel(self, position: BoardPosition) -> PixelPosition:
        return (
            BOARD_ORIGIN_X + position[0] * GRID_SIZE,
            BOARD_ORIGIN_Y + position[1] * GRID_SIZE,
        )

    def mouse_to_board(self, position: PixelPosition) -> BoardPosition | None:
        raw_x = (position[0] - BOARD_ORIGIN_X) / GRID_SIZE
        raw_y = (position[1] - BOARD_ORIGIN_Y) / GRID_SIZE
        board_x, board_y = round(raw_x), round(raw_y)
        if not (0 <= board_x < BOARD_COLS and 0 <= board_y < BOARD_ROWS):
            return None
        pixel = self.board_to_pixel((board_x, board_y))
        if math.dist(position, pixel) > PIECE_RADIUS + 8:
            return None
        return board_x, board_y

    # ---------- Rectangles ----------

    @staticmethod
    def menu_start_rect() -> pygame.Rect:
        return pygame.Rect(WINDOW_WIDTH // 2 - 190, 515, 380, 64)

    @staticmethod
    def language_rects() -> dict[Language, pygame.Rect]:
        languages: tuple[Language, ...] = ("zh", "en", "fr")
        width, gap = 120, 12
        total_width = len(languages) * width + (len(languages) - 1) * gap
        start_x = (WINDOW_WIDTH - total_width) // 2
        return {
            language: pygame.Rect(start_x + index * (width + gap), 455, width, 42)
            for index, language in enumerate(languages)
        }

    @staticmethod
    def finish_setup_rect() -> pygame.Rect:
        return pygame.Rect(SIDEBAR_X + 56, 694, SIDEBAR_WIDTH - 112, 55)

    @staticmethod
    def handoff_button_rect() -> pygame.Rect:
        return pygame.Rect(WINDOW_WIDTH // 2 - 155, 490, 310, 66)

    @staticmethod
    def catalog_rects() -> list[pygame.Rect]:
        rects = []
        item_width, item_height = 224, 54
        start_x, start_y = SIDEBAR_X + 24, 220
        for index in range(len(PIECE_CATALOG)):
            col, row = index % 2, index // 2
            rects.append(
                pygame.Rect(
                    start_x + col * (item_width + 18),
                    start_y + row * (item_height + 10),
                    item_width,
                    item_height,
                )
            )
        return rects

    @staticmethod
    def promotion_rects() -> dict[str, pygame.Rect]:
        kinds = ("queen", "rook", "bishop", "knight")
        item_width, gap = 125, 10
        total_width = len(kinds) * item_width + (len(kinds) - 1) * gap
        start_x = (WINDOW_WIDTH - total_width) // 2
        return {
            kind: pygame.Rect(start_x + index * (item_width + gap), 410, item_width, 62)
            for index, kind in enumerate(kinds)
        }

    @staticmethod
    def game_over_rects() -> tuple[pygame.Rect, pygame.Rect]:
        return (
            pygame.Rect(WINDOW_WIDTH // 2 - 230, 500, 210, 62),
            pygame.Rect(WINDOW_WIDTH // 2 + 20, 500, 210, 62),
        )

    # ---------- Drawing ----------

    def draw(self) -> None:
        self.screen.fill(COLORS["background"])
        if self.state == "menu":
            self.draw_menu()
            return
        if self.state == "handoff":
            self.draw_handoff()
            return

        visible_side = self.setup_side if self.state == "setup" else None
        self.draw_board(visible_side)
        if self.state == "setup":
            self.draw_setup_sidebar()
        else:
            self.draw_play_sidebar()
        if self.pending_promotion is not None:
            self.draw_promotion_modal()
        if self.state == "game_over":
            self.draw_game_over_modal()

    def draw_menu(self) -> None:
        self.draw_text(
            self.tr("menu.title"),
            self.fonts["title"],
            COLORS["text"],
            (640, 150),
            center=True,
        )
        self.draw_text(
            self.tr("menu.subtitle"),
            self.fonts["subtitle"],
            COLORS["accent"],
            (640, 215),
            center=True,
        )
        cards = [
            ("40", self.tr("menu.budget")),
            ("2", self.tr("menu.rulesets")),
            ("1", self.tr("menu.king")),
        ]
        for index, (number, label) in enumerate(cards):
            rect = pygame.Rect(300 + index * 235, 300, 210, 130)
            pygame.draw.rect(self.screen, COLORS["panel"], rect, border_radius=14)
            pygame.draw.rect(self.screen, (215, 205, 187), rect, 2, border_radius=14)
            self.draw_text(
                number,
                self.fonts["title"],
                COLORS["accent"],
                (rect.centerx, 338),
                center=True,
            )
            self.draw_text(
                label,
                self.fonts["small"],
                COLORS["muted"],
                (rect.centerx, 395),
                center=True,
            )
        for language, rect in self.language_rects().items():
            self.draw_button(
                rect,
                LANGUAGE_LABELS[language],
                active=language == self.language,
            )
        self.draw_button(self.menu_start_rect(), self.tr("menu.start"), active=True)
        self.draw_text(
            self.tr("menu.tagline"),
            self.fonts["small"],
            COLORS["muted"],
            (640, 630),
            center=True,
        )
        self.draw_text(
            self.tr("menu.escape"),
            self.fonts["tiny"],
            COLORS["muted"],
            (640, 720),
            center=True,
        )

    def draw_board(self, visible_side: Side | None) -> None:
        board_left = BOARD_ORIGIN_X - 42
        board_top = BOARD_ORIGIN_Y - 42
        board_width = (BOARD_COLS - 1) * GRID_SIZE + 84
        board_height = (BOARD_ROWS - 1) * GRID_SIZE + 84
        panel_rect = pygame.Rect(board_left, board_top, board_width, board_height)
        pygame.draw.rect(self.screen, COLORS["board"], panel_rect, border_radius=8)
        pygame.draw.rect(
            self.screen, COLORS["board_dark"], panel_rect, 3, border_radius=8
        )

        if self.state == "setup":
            rows = sorted(DEPLOYMENT_ROWS[self.setup_side])
            top_y = self.board_to_pixel((0, rows[0]))[1] - GRID_SIZE // 2
            height = (rows[-1] - rows[0] + 1) * GRID_SIZE
            highlight = pygame.Surface(
                ((BOARD_COLS - 1) * GRID_SIZE + 56, height), pygame.SRCALPHA
            )
            team_color = TEAM_COLORS[self.setup_side]
            highlight.fill((*team_color, 34))
            self.screen.blit(highlight, (BOARD_ORIGIN_X - 28, top_y))

        line_color = COLORS["board_dark"]
        for row in range(BOARD_ROWS):
            start = self.board_to_pixel((0, row))
            end = self.board_to_pixel((BOARD_COLS - 1, row))
            pygame.draw.line(self.screen, line_color, start, end, 2)
        for col in range(BOARD_COLS):
            if col in (0, BOARD_COLS - 1):
                pygame.draw.line(
                    self.screen,
                    line_color,
                    self.board_to_pixel((col, 0)),
                    self.board_to_pixel((col, BOARD_ROWS - 1)),
                    2,
                )
            else:
                pygame.draw.line(
                    self.screen,
                    line_color,
                    self.board_to_pixel((col, 0)),
                    self.board_to_pixel((col, 4)),
                    2,
                )
                pygame.draw.line(
                    self.screen,
                    line_color,
                    self.board_to_pixel((col, 5)),
                    self.board_to_pixel((col, 9)),
                    2,
                )
        # Palace diagonals.
        for top_row in (0, 7):
            pygame.draw.line(
                self.screen,
                line_color,
                self.board_to_pixel((3, top_row)),
                self.board_to_pixel((5, top_row + 2)),
                2,
            )
            pygame.draw.line(
                self.screen,
                line_color,
                self.board_to_pixel((5, top_row)),
                self.board_to_pixel((3, top_row + 2)),
                2,
            )

        self.draw_text(
            "楚 河", self.fonts["subtitle"], line_color, (240, 398), center=True
        )
        self.draw_text(
            "漢 界",
            self.fonts["subtitle"],
            line_color,
            (465, 398),
            center=True,
            rotation=180,
        )

        if self.selected_piece is not None and self.state == "playing":
            pygame.draw.circle(
                self.screen,
                COLORS["selected"],
                self.board_to_pixel(self.selected_piece.position),
                PIECE_RADIUS + 7,
                5,
            )
        for piece in self.pieces:
            if visible_side is None or piece.side == visible_side:
                self.draw_piece(piece, self.board_to_pixel(piece.position))

        for target in self.available_moves:
            occupant = self.piece_at(target)
            color = COLORS["capture"] if occupant else COLORS["move"]
            radius = 30 if occupant else 9
            pygame.draw.circle(
                self.screen,
                color,
                self.board_to_pixel(target),
                radius,
                4 if occupant else 0,
            )

    def draw_piece(self, piece: Piece, center: PixelPosition) -> None:
        team_color = TEAM_COLORS[piece.side]
        image = self.images.get((piece.game, piece.kind, piece.side))
        if image is not None:
            scaled_image = pygame.transform.smoothscale(image, (48, 48))
            self.screen.blit(scaled_image, scaled_image.get_rect(center=center))
            return

        pygame.draw.circle(self.screen, (246, 229, 192), center, PIECE_RADIUS)
        pygame.draw.circle(self.screen, team_color, center, PIECE_RADIUS, 3)
        self.draw_text(
            piece.label(), self.fonts["piece"], team_color, center, center=True
        )

    def draw_setup_sidebar(self) -> None:
        self.draw_sidebar_panel()
        side_color = TEAM_COLORS[self.setup_side]
        self.draw_text(
            self.tr("setup.title", side=self.side_name(self.setup_side)),
            self.fonts["subtitle"],
            side_color,
            (SIDEBAR_X + 28, 64),
        )
        self.draw_text(
            self.tr(
                "setup.budget",
                budget=self.budgets[self.setup_side],
                total=STARTING_BUDGET,
            ),
            self.fonts["body"],
            COLORS["text"],
            (SIDEBAR_X + 28, 112),
        )
        self.draw_text(
            self.tr(
                "setup.count",
                count=self.bought_totals[self.setup_side],
                maximum=MAX_BOUGHT_PIECES,
            ),
            self.fonts["small"],
            COLORS["muted"],
            (SIDEBAR_X + 290, 116),
        )
        self.draw_text(
            self.tr("setup.instructions"),
            self.fonts["small"],
            COLORS["muted"],
            (SIDEBAR_X + 28, 158),
        )
        self.draw_text(
            self.tr("setup.shop"),
            self.fonts["body"],
            COLORS["text"],
            (SIDEBAR_X + 28, 188),
        )

        for index, (item, rect) in enumerate(zip(PIECE_CATALOG, self.catalog_rects())):
            if item["kind"] == "king":
                continue
            active = self.can_buy(index)
            selected = self.selected_catalog_index == index
            fill = COLORS["panel"] if active else (224, 220, 211)
            if selected:
                fill = (255, 239, 189)
            pygame.draw.rect(self.screen, fill, rect, border_radius=9)
            border = COLORS["selected"] if selected else (198, 191, 179)
            pygame.draw.rect(
                self.screen, border, rect, 3 if selected else 1, border_radius=9
            )
            text_color = COLORS["text"] if active else COLORS["muted"]
            piece_sample = Piece(0, item["game"], item["kind"], self.setup_side, (0, 0))
            self.draw_piece(piece_sample, (rect.x + 30, rect.y + 27))
            key = (self.setup_side, item["game"], item["kind"])
            count = self.purchase_counts.get(key, 0)
            self.draw_text(
                self.tr(
                    "setup.price",
                    cost=item["cost"],
                    count=count,
                    limit=item["limit"],
                ),
                self.fonts["tiny"],
                text_color,
                (rect.x + 80, rect.y + 34),
            )

        self.draw_text(
            self.status, self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 662)
        )
        self.draw_button(self.finish_setup_rect(), self.tr("setup.finish"), active=True)

    def draw_play_sidebar(self) -> None:
        self.draw_sidebar_panel()
        self.draw_text(
            self.tr("play.title"),
            self.fonts["subtitle"],
            COLORS["text"],
            (SIDEBAR_X + 28, 64),
        )
        turn_color = TEAM_COLORS[self.turn]
        self.draw_text(
            self.tr("play.turn", side=self.side_name(self.turn)),
            self.fonts["button"],
            turn_color,
            (SIDEBAR_X + 28, 118),
        )
        pygame.draw.line(
            self.screen,
            (210, 202, 188),
            (SIDEBAR_X + 28, 165),
            (WINDOW_WIDTH - 38, 165),
            2,
        )
        if self.is_checked(self.turn):
            self.draw_text(
                self.tr("play.checked", side=self.side_name(self.turn)),
                self.fonts["body"],
                COLORS["text"],
                (SIDEBAR_X + 28, 195),
            )

        pygame.draw.line(
            self.screen,
            (210, 202, 188),
            (SIDEBAR_X + 28, 350),
            (WINDOW_WIDTH - 38, 350),
            2,
        )
        self.draw_text(
            self.tr("play.rules"),
            self.fonts["body"],
            COLORS["text"],
            (SIDEBAR_X + 28, 380),
        )
        rules = (
            self.tr("play.rule.moves"),
            self.tr("play.rule.king"),
            self.tr("play.rule.promotion"),
            self.tr("play.rule.xiangqi"),
        )
        for index, rule in enumerate(rules):
            self.draw_text(
                rule,
                self.fonts["small"],
                COLORS["muted"],
                (SIDEBAR_X + 28, 422 + index * 40),
            )

        pygame.draw.line(
            self.screen,
            (210, 202, 188),
            (SIDEBAR_X + 28, 600),
            (WINDOW_WIDTH - 38, 600),
            2,
        )
        self.draw_text(
            self.tr("play.status"),
            self.fonts["body"],
            COLORS["text"],
            (SIDEBAR_X + 28, 630),
        )

        self.draw_text(
            self.status, self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 672)
        )
        self.draw_text(
            self.tr("play.escape"),
            self.fonts["tiny"],
            COLORS["muted"],
            (SIDEBAR_X + 28, 735),
        )

    def draw_handoff(self) -> None:
        self.screen.fill(COLORS["overlay"])
        if self.handoff_target == "black":
            prefix = "handoff.red"
        else:
            prefix = "handoff.play"
        title = self.tr(f"{prefix}.title")
        body = self.tr(f"{prefix}.body")
        button = self.tr(f"{prefix}.button")
        self.draw_text(
            title, self.fonts["title"], COLORS["white"], (640, 260), center=True
        )
        self.draw_text(
            body, self.fonts["body"], (202, 207, 213), (640, 350), center=True
        )
        self.draw_button(self.handoff_button_rect(), button, active=True)
        self.draw_text(
            self.tr("handoff.privacy"),
            self.fonts["small"],
            (145, 151, 159),
            (640, 610),
            center=True,
        )

    def draw_promotion_modal(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 18, 20, 185))
        self.screen.blit(overlay, (0, 0))
        modal = pygame.Rect(WINDOW_WIDTH // 2 - 290, 285, 580, 245)
        pygame.draw.rect(self.screen, COLORS["panel"], modal, border_radius=16)
        self.draw_text(
            self.tr("promotion.title"),
            self.fonts["subtitle"],
            COLORS["text"],
            (640, 338),
            center=True,
        )
        for kind, rect in self.promotion_rects().items():
            self.draw_button(rect, self.tr(f"promotion.{kind}"), active=True)

    def draw_game_over_modal(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 18, 20, 195))
        self.screen.blit(overlay, (0, 0))
        modal = pygame.Rect(WINDOW_WIDTH // 2 - 320, 245, 640, 365)
        pygame.draw.rect(self.screen, COLORS["panel"], modal, border_radius=18)
        winner = self.side_name(self.winner or "red")
        self.draw_text(
            self.tr("game_over.title"),
            self.fonts["subtitle"],
            COLORS["muted"],
            (640, 310),
            center=True,
        )
        self.draw_text(
            self.tr("game_over.winner", side=winner),
            self.fonts["title"],
            TEAM_COLORS[self.winner or "red"],
            (640, 385),
            center=True,
        )
        self.draw_text(
            self.tr("game_over.reason"),
            self.fonts["body"],
            COLORS["text"],
            (640, 445),
            center=True,
        )
        restart, menu = self.game_over_rects()
        self.draw_button(restart, self.tr("game_over.restart"), active=True)
        self.draw_button(menu, self.tr("game_over.menu"), active=False)

    def draw_sidebar_panel(self) -> None:
        rect = pygame.Rect(SIDEBAR_X, 28, SIDEBAR_WIDTH, WINDOW_HEIGHT - 56)
        pygame.draw.rect(self.screen, COLORS["panel"], rect, border_radius=15)
        pygame.draw.rect(self.screen, (211, 203, 190), rect, 2, border_radius=15)

    def draw_button(self, rect: pygame.Rect, label: str, active: bool) -> None:
        mouse_over = rect.collidepoint(pygame.mouse.get_pos())
        if active:
            color = COLORS["accent_hover"] if mouse_over else COLORS["accent"]
            text_color = COLORS["white"]
        else:
            color = (224, 219, 210)
            text_color = COLORS["text"]
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        self.draw_text(
            label, self.fonts["button"], text_color, rect.center, center=True
        )

    def draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        position: PixelPosition,
        *,
        center: bool = False,
        rotation: int = 0,
    ) -> None:
        surface = font.render(text, True, color)
        if rotation:
            surface = pygame.transform.rotate(surface, rotation)
        rect = surface.get_rect()
        if center:
            rect.center = position
        else:
            rect.topleft = position
        self.screen.blit(surface, rect)


def main() -> None:
    game = HybridChessGame()
    game.run()


if __name__ == "__main__":
    main()
