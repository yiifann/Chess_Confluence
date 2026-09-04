"""Hybrid Chess Demo: Chinese chess meets international chess."""

from __future__ import annotations

import math
import sys
from pathlib import Path

try:
    import pygame
except ImportError:  # Friendly message when launched before dependencies exist.
    print("缺少 pygame。请先运行：python -m pip install -r requirements.txt")
    raise SystemExit(1)

from pieces import Piece, legal_moves
from pieces import Position_grid, Game, Side
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
)
Position_pixel = tuple[int, int]


def find_cjk_font() -> str | None:
    """Pick a commonly available CJK font on Windows, macOS, or Linux."""
    candidates = (
        "microsoftyahei",
        "microsoftjhenghei",
        "pingfangsc",
        "hiraginosansgb",
        "notosanscjksc",
        "sourcehansanscn",
        "wenquanyimicrohei",
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
        pygame.display.set_caption("融合棋局 · Hybrid Chess Demo")
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
        self.state = "menu"
        # load piece images
        self.load_images()
        self.reset_match()

    def load_images(self):
        self.images = {}
        for piece in PIECE_CATALOG:
            self.images[piece["kind"]] = {}
            # print(Path(__file__).parent / "assets" / piece["images"]["red"])
            try:
                self.images[piece["kind"]]["red"] = pygame.image.load(Path(__file__).parent / "assets" / piece["images"]["red"]).convert_alpha()
                self.images[piece["kind"]]["black"] = pygame.image.load(Path(__file__).parent / "assets" / piece["images"]["black"]).convert_alpha()
            except:
                pass

    def is_checked(self, side : Side) -> bool:
        for piece in self.pieces: 
            if self.kings[side].position in legal_moves(piece=piece, pieces=self.pieces):
                return True
        return False

    def reset_match(self) -> None:
        self.pieces: list[Piece] = [
            Piece(1, "xiangqi", "king", "red", (4, 9)),
            Piece(2, "xiangqi", "king", "black", (4, 0)),
        ]
        self.kings: dict[Side : Piece] = {
            "red": self.pieces[0],
            "black": self.pieces[1]
        }
        self.next_piece_id = 3
        self.budgets = {"red": STARTING_BUDGET, "black": STARTING_BUDGET}
        self.purchase_counts: dict[tuple[str, str, str], int] = {}
        self.bought_totals = {"red": 0, "black": 0}
        self.setup_side = "red"
        self.selected_catalog_index: int | None = None
        self.selected_piece: Piece | None = None
        self.available_moves: list[Position_grid] = []
        self.turn = "red"
        self.winner: Side | None = None
        self.pending_promotion: Piece | None = None
        self.handoff_target = "black"
        self.status = "红方请选择棋子并在己方后四行部署。"

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

    def handle_menu_click(self, position: Position_pixel) -> None:
        if self.menu_start_rect().collidepoint(position):
            self.reset_match()
            self.state = "setup"

    def handle_setup_click(self, position: Position_pixel, button: int) -> None:
        if button == 1:
            for index, rect in enumerate(self.catalog_rects()):
                if rect.collidepoint(position):
                    if self.can_buy(index):
                        self.selected_catalog_index = index
                        item = PIECE_CATALOG[index]
                        self.status = f"已选择{item['name']}，点击高亮部署区放置。"
                    else:
                        self.status = "资金不足、已达该棋子上限，或总棋子数已满。"
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

    def handle_handoff_click(self, position: Position_pixel) -> None:
        if not self.handoff_button_rect().collidepoint(position):
            return
        if self.handoff_target == "black":
            self.setup_side = "black"
            self.selected_catalog_index = None
            self.status = "黑方请选择棋子并在己方前三行部署。"
            self.state = "setup"
        else:
            self.turn = "red"
            self.status = "红方先行：点击己方棋子查看合法落点。"
            self.state = "playing"

    def handle_play_click(self, position: Position_pixel, button: int) -> None:
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
            self.status = f"已选择 {self.describe_piece(clicked_piece)}。"
            return
        self.selected_piece = None
        self.available_moves = []
        self.status = "这里没有本方可操作的棋子。"

    def handle_game_over_click(self, position: Position_pixel) -> None:
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

    def try_place_piece(self, position: Position_grid) -> None:
        if self.selected_catalog_index is None:
            self.status = "请先从右侧商店选择一种棋子。"
            return
        if position[1] not in DEPLOYMENT_ROWS[self.setup_side]:
            self.status = "只能将棋子放在己方的三行部署区内。"
            return
        if self.piece_at(position) is not None:
            self.status = "这个位置已经有棋子了。"
            return
        if not self.can_buy(self.selected_catalog_index):
            self.status = "当前已无法购买这枚棋子。"
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
        self.status = f"已部署{item['name']}，剩余资金 {self.budgets[self.setup_side]}。"
        if not self.can_buy(self.selected_catalog_index):
            self.selected_catalog_index = None

    def try_remove_piece(self, position: Position_grid) -> None:
        piece = self.piece_at(position)
        if piece is None or piece.side != self.setup_side:
            self.status = "右键点击己方已购买的棋子可以撤回并退款。"
            return
        if piece.kind == "king":
            self.status = "将/帅的位置固定，不能撤回。"
            return
        item = self.catalog_item_for(piece)
        self.pieces.remove(piece)
        self.budgets[self.setup_side] += item["cost"]
        key = (piece.side, piece.game, piece.kind)
        self.purchase_counts[key] -= 1
        self.bought_totals[self.setup_side] -= 1
        self.status = f"已撤回{item['name']}并退还 {item['cost']} 点资金。"

    def finish_setup(self) -> None:
        self.selected_catalog_index = None
        self.state = "handoff"
        if self.setup_side == "red":
            self.handoff_target = "black"
        else:
            self.handoff_target = "play"

    # ---------- Battle logic ----------

    def move_selected_piece(self, target: Position_grid) -> None:
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
            self.status = f"{self.side_name(piece.side)}吃掉了对方的将帅。"
            self.state = "game_over"
            return

        final_row = 0 if piece.side == "red" else BOARD_ROWS - 1
        if piece.game == "chess" and piece.kind == "pawn" and target[1] == final_row:
            self.pending_promotion = piece
            self.status = "国际象棋兵到达底线，请选择升变棋子。"
            return
        self.end_turn()

    def end_turn(self) -> None:
        self.turn = "black" if self.turn == "red" else "red"
        self.status = f"轮到{self.side_name(self.turn)}行动。"

    # ---------- Lookup and coordinates ----------

    def piece_at(self, position: Position_grid) -> Piece | None:
        return next((piece for piece in self.pieces if piece.position == position), None)

    @staticmethod
    def catalog_item_for(piece: Piece) -> dict:
        return next(
            item
            for item in PIECE_CATALOG
            if item["game"] == piece.game and item["kind"] == piece.kind
        )

    @staticmethod
    def side_name(side: Side) -> str:
        return "红方" if side == "red" else "黑方"

    @staticmethod
    def describe_piece(piece: Piece) -> str:
        game_name = "中国象棋" if piece.game == "xiangqi" else "国际象棋"
        return f"{game_name}·{piece.label()}"

    def board_to_pixel(self, position: Position_pixel) -> Position_pixel:
        return (
            BOARD_ORIGIN_X + position[0] * GRID_SIZE,
            BOARD_ORIGIN_Y + position[1] * GRID_SIZE,
        )

    def mouse_to_board(self, position: Position_pixel) -> Position_pixel | None:
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
        return pygame.Rect(WINDOW_WIDTH // 2 - 130, 515, 260, 64)

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
        start_x = WINDOW_WIDTH // 2 - 230
        return {
            kind: pygame.Rect(start_x + index * 120, 410, 100, 62)
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
        self.draw_text("融合棋局", self.fonts["title"], COLORS["text"], (640, 150), center=True)
        self.draw_text(
            "中国象棋 × 国际象棋",
            self.fonts["subtitle"],
            COLORS["accent"],
            (640, 215),
            center=True,
        )
        cards = [
            ("40", "点初始资金"),
            ("2", "套棋子规则"),
            ("1", "个需要守护的帅"),
        ]
        for index, (number, label) in enumerate(cards):
            rect = pygame.Rect(300 + index * 235, 300, 210, 130)
            pygame.draw.rect(self.screen, COLORS["panel"], rect, border_radius=14)
            pygame.draw.rect(self.screen, (215, 205, 187), rect, 2, border_radius=14)
            self.draw_text(number, self.fonts["title"], COLORS["accent"], (rect.centerx, 338), center=True)
            self.draw_text(label, self.fonts["small"], COLORS["muted"], (rect.centerx, 395), center=True)
        self.draw_button(self.menu_start_rect(), "开始本地双人对局", active=True)
        self.draw_text(
            "双方秘密购买并部署不同棋子，率先吃掉对方将帅者获胜",
            self.fonts["small"],
            COLORS["muted"],
            (640, 630),
            center=True,
        )
        self.draw_text("ESC 退出", self.fonts["tiny"], COLORS["muted"], (640, 720), center=True)

    def draw_board(self, visible_side: Side | None) -> None:
        board_left = BOARD_ORIGIN_X - 42
        board_top = BOARD_ORIGIN_Y - 42
        board_width = (BOARD_COLS - 1) * GRID_SIZE + 84
        board_height = (BOARD_ROWS - 1) * GRID_SIZE + 84
        panel_rect = pygame.Rect(board_left, board_top, board_width, board_height)
        pygame.draw.rect(self.screen, COLORS["board"], panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["board_dark"], panel_rect, 3, border_radius=8)

        if self.state == "setup":
            rows = sorted(DEPLOYMENT_ROWS[self.setup_side])
            top_y = self.board_to_pixel((0, rows[0]))[1] - GRID_SIZE // 2
            height = (rows[-1] - rows[0] + 1) * GRID_SIZE
            highlight = pygame.Surface(((BOARD_COLS - 1) * GRID_SIZE + 56, height), pygame.SRCALPHA)
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

        self.draw_text("楚 河", self.fonts["subtitle"], line_color, (240, 398), center=True)
        self.draw_text("漢 界", self.fonts["subtitle"], line_color, (465, 398), center=True, rotation=180)

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
            pygame.draw.circle(self.screen, color, self.board_to_pixel(target), radius, 4 if occupant else 0)



    # TODO: update draw_piece method
    def draw_piece(self, piece: Piece, center: Position_pixel) -> None:
        team_color = TEAM_COLORS[piece.side]
        if piece.game == "xiangqi":
            pygame.draw.circle(self.screen, (246, 229, 192), center, PIECE_RADIUS)
            pygame.draw.circle(self.screen, team_color, center, PIECE_RADIUS, 3)
            pygame.draw.circle(self.screen, team_color, center, PIECE_RADIUS - 5, 1)
            self.draw_text(piece.label(), self.fonts["piece"], team_color, center, center=True)
        else:
            image = self.images[piece.kind][piece.side]
            self.screen.blit(image, image.get_rect(center=center))
            # rect = pygame.Rect(0, 0, PIECE_RADIUS * 2, PIECE_RADIUS * 2)
            # rect.center = center
            # pygame.draw.rect(self.screen, team_color, rect, border_radius=8)
            # pygame.draw.rect(self.screen, COLORS["white"], rect, 2, border_radius=8)
            # self.draw_text(piece.label(), self.fonts["piece"], COLORS["white"], center, center=True)
            # badge_center = (rect.left + 8, rect.top + 8)
            # pygame.draw.circle(self.screen, COLORS["white"], badge_center, 6)
            # pygame.draw.circle(self.screen, team_color, badge_center, 3)

    def draw_setup_sidebar(self) -> None:
        self.draw_sidebar_panel()
        side_color = TEAM_COLORS[self.setup_side]
        self.draw_text(
            f"{self.side_name(self.setup_side)}秘密部署",
            self.fonts["subtitle"],
            side_color,
            (SIDEBAR_X + 28, 64),
        )
        self.draw_text(
            f"剩余资金  {self.budgets[self.setup_side]} / {STARTING_BUDGET}",
            self.fonts["body"],
            COLORS["text"],
            (SIDEBAR_X + 28, 112),
        )
        self.draw_text(
            f"已购棋子  {self.bought_totals[self.setup_side]} / {MAX_BOUGHT_PIECES}",
            self.fonts["small"],
            COLORS["muted"],
            (SIDEBAR_X + 290, 116),
        )
        self.draw_text("选中商品后点击高亮交叉点；右键撤回并退款", self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 158))
        self.draw_text("棋子商店", self.fonts["body"], COLORS["text"], (SIDEBAR_X + 28, 188))

        for index, (item, rect) in enumerate(zip(PIECE_CATALOG, self.catalog_rects())):
            active = self.can_buy(index)
            selected = self.selected_catalog_index == index
            fill = COLORS["panel"] if active else (224, 220, 211)
            if selected:
                fill = (255, 239, 189)
            pygame.draw.rect(self.screen, fill, rect, border_radius=9)
            border = COLORS["selected"] if selected else (198, 191, 179)
            pygame.draw.rect(self.screen, border, rect, 3 if selected else 1, border_radius=9)
            text_color = COLORS["text"] if active else COLORS["muted"]
            # Change the text to image
            # self.draw_text(item["name"], self.fonts["small"], text_color, (rect.x + 12, rect.y + 9))
            piece_sample = Piece(None, item["game"], item["kind"], self.turn, None, None)
            self.draw_piece(piece_sample, (rect.x + 30, rect.y + 27))
            key = (self.setup_side, item["game"], item["kind"])
            count = self.purchase_counts.get(key, 0)
            self.draw_text(
                f"{item['cost']}点   {count}/{item['limit']}",
                self.fonts["tiny"],
                text_color,
                (rect.x + 80, rect.y + 34),
            )

        self.draw_text(self.status, self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 662))
        self.draw_button(self.finish_setup_rect(), "确认阵容并交接", active=True)

    def draw_play_sidebar(self) -> None:
        self.draw_sidebar_panel()
        self.draw_text("正式对局", self.fonts["subtitle"], COLORS["text"], (SIDEBAR_X + 28, 64))
        turn_color = TEAM_COLORS[self.turn]
        self.draw_text(
            f"当前回合：{self.side_name(self.turn)}",
            self.fonts["button"],
            turn_color,
            (SIDEBAR_X + 28, 118),
        )
        pygame.draw.line(self.screen, (210, 202, 188), (SIDEBAR_X + 28, 165), (WINDOW_WIDTH - 38, 165), 2)
        if self.is_checked(self.turn):
            self.draw_text(self.side_name(self.turn) + "已被将军！", self.fonts["body"], COLORS["text"], (SIDEBAR_X + 28, 195))
        # self.draw_text("棋子识别", self.fonts["body"], COLORS["text"], (SIDEBAR_X + 28, 195))
        # self.draw_text("圆形汉字： 中国象棋棋子", self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 235))
        # self.draw_text("方形字母： 国际象棋棋子", self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 270))
        # self.draw_text("P兵  N马  B象  R车  Q后", self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 305))

        pygame.draw.line(self.screen, (210, 202, 188), (SIDEBAR_X + 28, 350), (WINDOW_WIDTH - 38, 350), 2)
        self.draw_text("本局规则", self.fonts["body"], COLORS["text"], (SIDEBAR_X + 28, 380))
        rules = (
            "• 点击本方棋子，绿色点为移动，红圈为吃子",
            "• 不判将军或将死，可直接吃掉对方将帅",
            "• 国际象棋兵（pawn）到底线后可升变",
            "• 中国象棋棋子保留蹩马腿、炮架等规则",
        )
        for index, rule in enumerate(rules):
            self.draw_text(rule, self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 422 + index * 40))

        pygame.draw.line(self.screen, (210, 202, 188), (SIDEBAR_X + 28, 600), (WINDOW_WIDTH - 38, 600), 2)
        self.draw_text("状态", self.fonts["body"], COLORS["text"], (SIDEBAR_X + 28, 630))

        self.draw_text(self.status, self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 672))
        self.draw_text("ESC 返回主菜单", self.fonts["tiny"], COLORS["muted"], (SIDEBAR_X + 28, 735))

    def draw_handoff(self) -> None:
        self.screen.fill(COLORS["overlay"])
        if self.handoff_target == "black":
            title = "红方部署完成"
            body = "请红方离开屏幕，然后把电脑交给黑方。"
            button = "我是黑方，开始部署"
            self.turn = "black"
        else:
            title = "双方部署完成"
            body = "阵容将在下一步同时公开，红方首先行动。"
            button = "公开阵容并开始"
            self.turn = "red"
        self.draw_text(title, self.fonts["title"], COLORS["white"], (640, 260), center=True)
        self.draw_text(body, self.fonts["body"], (202, 207, 213), (640, 350), center=True)
        self.draw_button(self.handoff_button_rect(), button, active=True)
        self.draw_text("此页面不会显示上一位玩家的阵容", self.fonts["small"], (145, 151, 159), (640, 610), center=True)

    def draw_promotion_modal(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 18, 20, 185))
        self.screen.blit(overlay, (0, 0))
        modal = pygame.Rect(WINDOW_WIDTH // 2 - 290, 285, 580, 245)
        pygame.draw.rect(self.screen, COLORS["panel"], modal, border_radius=16)
        self.draw_text("兵已到达底线：选择升变", self.fonts["subtitle"], COLORS["text"], (640, 338), center=True)
        names = {"queen": "Q 后", "rook": "R 车", "bishop": "B 象", "knight": "N 马"}
        for kind, rect in self.promotion_rects().items():
            self.draw_button(rect, names[kind], active=True)

    def draw_game_over_modal(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 18, 20, 195))
        self.screen.blit(overlay, (0, 0))
        modal = pygame.Rect(WINDOW_WIDTH // 2 - 320, 245, 640, 365)
        pygame.draw.rect(self.screen, COLORS["panel"], modal, border_radius=18)
        winner = self.side_name(self.winner or "red")
        self.draw_text("对局结束", self.fonts["subtitle"], COLORS["muted"], (640, 310), center=True)
        self.draw_text(f"{winner}获胜！", self.fonts["title"], TEAM_COLORS[self.winner or "red"], (640, 385), center=True)
        self.draw_text("成功吃掉了对方的将帅", self.fonts["body"], COLORS["text"], (640, 445), center=True)
        restart, menu = self.game_over_rects()
        self.draw_button(restart, "重新开局", active=True)
        self.draw_button(menu, "返回菜单", active=False)

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
        self.draw_text(label, self.fonts["button"], text_color, rect.center, center=True)

    def draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        position: Position_pixel,
        *,
        center: bool = False,
        rotation: int = False
    ) -> None:
        surface = font.render(text, True, color)
        # Text rotation
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

