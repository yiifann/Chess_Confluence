"""Pygame interface and state controller for Chess Confluence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    import pygame
except ImportError:  # Friendly message when launched before dependencies exist.
    print("pygame is missing. Run: python -m pip install -r requirements.txt")
    raise SystemExit(1)

from ai import (
    CatalogOption,
    GameObservation,
    GamePolicy,
    HeuristicPolicy,
    PieceView,
    SetupRequest,
    enumerate_legal_actions,
)
from i18n import LANGUAGE_LABELS, Language, translate
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
    BOARD_ORIGIN_X,
    BOARD_ORIGIN_Y,
    BOARD_ROWS,
    CHESS_KING_COST,
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
GameMode = Literal["single", "local"]
ImageKey = tuple[Game, str, Side]

AI_SIDE: Side = "black"
AI_MOVE_DELAY_MS = 450
PROMOTION_OPTIONS = ("queen", "rook", "bishop", "knight")


@dataclass(frozen=True)
class MovementPreview:
    moves: tuple[BoardPosition, ...]
    captures: tuple[BoardPosition, ...] = ()
    blockers: tuple[BoardPosition, ...] = ()
    blocker_label: Literal["blocker", "screen"] | None = None


ORTHOGONAL_MOVES = (
    (-2, 0),
    (-1, 0),
    (1, 0),
    (2, 0),
    (0, -2),
    (0, -1),
    (0, 1),
    (0, 2),
)
DIAGONAL_MOVES = (
    (-2, -2),
    (-1, -1),
    (1, -1),
    (2, -2),
    (-2, 2),
    (-1, 1),
    (1, 1),
    (2, 2),
)
KNIGHT_MOVES = (
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
)

MOVEMENT_PREVIEWS: dict[tuple[Game, str], MovementPreview] = {
    ("xiangqi", "king"): MovementPreview(((0, -1), (-1, 0), (1, 0), (0, 1))),
    ("xiangqi", "bing"): MovementPreview(((0, -1), (-1, 0), (1, 0))),
    ("xiangqi", "advisor"): MovementPreview(((-1, -1), (1, -1), (-1, 1), (1, 1))),
    ("xiangqi", "elephant"): MovementPreview(
        ((-2, -2), (-2, 2), (2, 2)),
        blockers=((1, -1),),
        blocker_label="blocker",
    ),
    ("xiangqi", "horse"): MovementPreview(
        tuple(move for move in KNIGHT_MOVES if move[0] < 2),
        blockers=((1, 0),),
        blocker_label="blocker",
    ),
    ("xiangqi", "cannon"): MovementPreview(
        ((0, -2), (0, -1), (0, 1), (0, 2)),
        captures=((-2, 0), (2, 0)),
        blockers=((-1, 0), (1, 0)),
        blocker_label="screen",
    ),
    ("xiangqi", "rook"): MovementPreview(ORTHOGONAL_MOVES),
    ("chess", "pawn"): MovementPreview(((0, -1), (0, -2)), ((-1, -1), (1, -1))),
    ("chess", "knight"): MovementPreview(KNIGHT_MOVES),
    ("chess", "bishop"): MovementPreview(DIAGONAL_MOVES),
    ("chess", "rook"): MovementPreview(ORTHOGONAL_MOVES),
    ("chess", "queen"): MovementPreview(ORTHOGONAL_MOVES + DIAGONAL_MOVES),
    ("chess", "king"): MovementPreview(
        ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
    ),
}


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
    """Own the live match state and coordinate Pygame, rules, and AI policies.

    Movement generation remains in ``pieces.py`` and policy decisions remain in
    ``ai.py``. This controller is the only layer that mutates a live match.
    """

    def __init__(self, ai_policy: GamePolicy | None = None) -> None:
        pygame.init()
        self.language: Language = "zh"
        self.game_mode: GameMode = "single"
        self.ai_policy: GamePolicy = (
            ai_policy if ai_policy is not None else HeuristicPolicy()
        )
        pygame.display.set_caption(self.tr("window_title"))
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_path = find_cjk_font()
        self.fonts = {
            "micro": pygame.font.Font(self.font_path, 13),
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
        """Report whether the leader is capturable next turn for UI feedback."""
        king_position = self.kings[side].position
        return any(
            piece.side != side and king_position in legal_moves(piece, self.pieces)
            for piece in self.pieces
        )

    def reset_match(self) -> None:
        """Restore a fresh Red-first setup while preserving language and mode."""
        self.pieces: list[Piece] = [
            Piece(1, "xiangqi", "king", "red", (4, 9)),
            Piece(2, "xiangqi", "king", "black", (4, 0)),
        ]
        self.kings: dict[Side, Piece] = {"red": self.pieces[0], "black": self.pieces[1]}
        self.next_piece_id = 3
        self.budgets: dict[Side, float] = {
            "red": STARTING_BUDGET,
            "black": STARTING_BUDGET,
        }
        self.purchase_counts: dict[tuple[Side, Game, str], int] = {}
        self.bought_totals: dict[Side, int] = {"red": 0, "black": 0}
        self.setup_side: Side = "red"
        self.selected_catalog_index: int | None = None
        self.selected_setup_king = False
        self.selected_piece: Piece | None = None
        self.available_moves: list[BoardPosition] = []
        self.turn: Side = "red"
        self.winner: Side | None = None
        self.pending_promotion: Piece | None = None
        self.ai_move_due_at: int | None = None
        self.handoff_target: HandoffTarget = "black"
        self.status = self.tr("status.setup.red")

    # ---------- Main loop and events ----------

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.update_ai()
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
        for game_mode, rect in self.game_mode_rects().items():
            if rect.collidepoint(position):
                self.game_mode = game_mode
                return
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
            for game, rect in self.king_choice_rects().items():
                if rect.collidepoint(position):
                    self.select_king_type(game)
                    return
            for index, rect in self.catalog_rects().items():
                if rect.collidepoint(position):
                    if self.can_buy(index):
                        self.selected_catalog_index = index
                        self.selected_setup_king = False
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
            clicked_piece = self.piece_at(board_position)
            if (
                not self.selected_setup_king
                and clicked_piece is self.kings[self.setup_side]
            ):
                self.selected_catalog_index = None
                self.selected_setup_king = True
                self.status = self.tr(
                    "status.king_selected",
                    piece=self.describe_piece(clicked_piece),
                )
            elif self.selected_setup_king:
                self.try_place_king(board_position)
            else:
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
        if self.game_mode == "single" and self.turn == AI_SIDE:
            self.status = self.tr("status.ai_thinking")
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

    def select_king_type(self, game: Game) -> None:
        king = self.kings[self.setup_side]
        if king.game != game:
            if game == "chess":
                if self.budgets[self.setup_side] < CHESS_KING_COST:
                    self.status = self.tr("status.king_upgrade_unavailable")
                    return
                self.budgets[self.setup_side] -= CHESS_KING_COST
            else:
                self.budgets[self.setup_side] += CHESS_KING_COST
            king.game = game

        self.selected_catalog_index = None
        self.selected_setup_king = True
        self.status = self.tr("status.king_selected", piece=self.describe_piece(king))

    def try_place_king(self, position: BoardPosition) -> None:
        king = self.kings[self.setup_side]
        if not valid_king_setup_position(king, position):
            status_key = f"status.king_place_{king.game}"
            self.status = self.tr(status_key)
            return
        occupant = self.piece_at(position)
        if occupant is not None and occupant is not king:
            self.status = self.tr("status.occupied")
            return

        king.position = position
        self.selected_setup_king = False
        self.status = self.tr("status.king_placed", piece=self.describe_piece(king))

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
        """Leave setup through the single-player or privacy-handoff branch."""
        king = self.kings[self.setup_side]
        if not valid_king_setup_position(king, king.position):
            self.status = self.tr(f"status.king_place_{king.game}")
            self.selected_setup_king = True
            return
        self.selected_catalog_index = None
        self.selected_setup_king = False
        if self.game_mode == "single" and self.setup_side == "red":
            self.setup_ai_opponent()
            self.setup_side = "red"
            self.turn = "red"
            self.state = "playing"
            self.status = self.tr("status.ai_ready")
            return
        self.state = "handoff"
        if self.setup_side == "red":
            self.handoff_target = "black"
        else:
            self.handoff_target = "play"

    def setup_ai_opponent(self) -> None:
        """Ask the active policy for a setup and apply only validated choices."""
        side: Side = AI_SIDE
        request = SetupRequest(
            side=side,
            budget=STARTING_BUDGET,
            max_pieces=MAX_BOUGHT_PIECES,
            catalog=tuple(
                CatalogOption(item["game"], item["kind"], item["cost"], item["limit"])
                for item in PIECE_CATALOG
                if item["limit"] > 0
            ),
            deployment_rows=tuple(sorted(DEPLOYMENT_ROWS[side])),
            # Secret setup policies must not receive the human army's positions.
            occupied=(),
            chess_king_cost=CHESS_KING_COST,
            board_columns=BOARD_COLS,
            board_rows=BOARD_ROWS,
        )
        plan = self.ai_policy.choose_setup(request)
        king = self.kings[side]
        # Treat policy output as untrusted: future model adapters may emit an
        # invalid leader choice while exploring or loading an incompatible model.
        king.game = (
            plan.king_game if plan.king_game in ("chess", "xiangqi") else "xiangqi"
        )
        king_cost = CHESS_KING_COST if king.game == "chess" else 0
        if (
            king_cost > STARTING_BUDGET
            or not valid_king_setup_position(king, plan.king_position)
            or self.piece_at(plan.king_position) not in (None, king)
        ):
            king.game = "xiangqi"
            king.position = (4, 0)
            king_cost = 0
        else:
            king.position = plan.king_position

        self.budgets[side] = STARTING_BUDGET - king_cost
        for placement in plan.placements:
            matching_item = next(
                (
                    item
                    for item in PIECE_CATALOG
                    if item["limit"] > 0
                    and item["game"] == placement.game
                    and item["kind"] == placement.kind
                ),
                None,
            )
            if matching_item is None:
                continue
            key = (side, matching_item["game"], matching_item["kind"])
            # Validate every placement independently so one malformed action
            # cannot invalidate the rest of an otherwise usable setup plan.
            if (
                placement.position[1] not in DEPLOYMENT_ROWS[side]
                or not (0 <= placement.position[0] < BOARD_COLS)
                or self.piece_at(placement.position) is not None
                or self.purchase_counts.get(key, 0) >= matching_item["limit"]
                or self.bought_totals[side] >= MAX_BOUGHT_PIECES
                or self.budgets[side] < matching_item["cost"]
            ):
                continue
            self.pieces.append(
                Piece(
                    self.next_piece_id,
                    matching_item["game"],
                    matching_item["kind"],
                    side,
                    placement.position,
                )
            )
            self.next_piece_id += 1
            self.budgets[side] -= matching_item["cost"]
            self.purchase_counts[key] = self.purchase_counts.get(key, 0) + 1
            self.bought_totals[side] += 1

    # ---------- Battle logic ----------

    def move_selected_piece(self, target: BoardPosition) -> None:
        piece = self.selected_piece
        if piece is None:
            return
        self.execute_move(piece, target)

    def execute_move(
        self,
        piece: Piece,
        target: BoardPosition,
        promotion: str | None = None,
    ) -> None:
        """Apply a validated human or policy action to the live match."""
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
            if promotion in PROMOTION_OPTIONS:
                piece.kind = promotion
                self.end_turn()
                return
            self.pending_promotion = piece
            self.status = self.tr("status.promote")
            return
        self.end_turn()

    def end_turn(self) -> None:
        """Advance the turn and schedule, but do not block on, an AI response."""
        self.turn = "black" if self.turn == "red" else "red"
        self.status = self.tr("status.turn", side=self.side_name(self.turn))
        if self.game_mode == "single" and self.turn == AI_SIDE:
            self.ai_move_due_at = pygame.time.get_ticks() + AI_MOVE_DELAY_MS
            self.status = self.tr("status.ai_thinking")
        else:
            self.ai_move_due_at = None

    def game_observation(self) -> GameObservation:
        """Create the immutable state passed to AI policies."""
        return GameObservation.from_pieces(
            self.turn,
            self.pieces,
            BOARD_COLS,
            BOARD_ROWS,
        )

    def update_ai(self) -> None:
        """Run a due AI turn from the frame loop, keeping the UI responsive."""
        if (
            self.game_mode != "single"
            or self.state != "playing"
            or self.turn != AI_SIDE
            or self.pending_promotion is not None
        ):
            return
        if self.ai_move_due_at is None:
            self.ai_move_due_at = pygame.time.get_ticks() + AI_MOVE_DELAY_MS
            return
        if pygame.time.get_ticks() < self.ai_move_due_at:
            return
        self.perform_ai_turn()

    def perform_ai_turn(self) -> None:
        """Request, validate, and execute one AI action immediately."""
        observation = self.game_observation()
        legal_actions = enumerate_legal_actions(observation, AI_SIDE)
        if not legal_actions:
            self.winner = "red"
            self.state = "game_over"
            self.status = self.tr("status.ai_no_moves")
            self.ai_move_due_at = None
            return
        action = self.ai_policy.choose_move(observation, legal_actions)
        # An RL adapter can return an out-of-mask action. Falling back keeps the
        # live game valid while allowing the adapter to log the model error.
        if action not in legal_actions:
            action = legal_actions[0]
        piece = next(
            live_piece
            for live_piece in self.pieces
            if live_piece.piece_id == action.piece_id
        )
        promotion = None
        final_row = BOARD_ROWS - 1
        if (
            piece.game == "chess"
            and piece.kind == "pawn"
            and action.target[1] == final_row
        ):
            promotion = self.ai_policy.choose_promotion(
                observation,
                PieceView.from_piece(piece),
                PROMOTION_OPTIONS,
            )
            if promotion not in PROMOTION_OPTIONS:
                promotion = "queen"
        description = self.describe_piece(piece)
        self.execute_move(piece, action.target, promotion)
        if self.state == "playing":
            self.status = self.tr(
                "status.ai_moved",
                piece=description,
                column=action.target[0] + 1,
                row=action.target[1] + 1,
            )

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
        return pygame.Rect(WINDOW_WIDTH // 2 - 190, 565, 380, 64)

    @staticmethod
    def game_mode_rects() -> dict[GameMode, pygame.Rect]:
        return {
            "single": pygame.Rect(WINDOW_WIDTH // 2 - 286, 450, 280, 42),
            "local": pygame.Rect(WINDOW_WIDTH // 2 + 6, 450, 280, 42),
        }

    @staticmethod
    def language_rects() -> dict[Language, pygame.Rect]:
        languages: tuple[Language, ...] = ("zh", "en", "fr")
        width, gap = 120, 12
        total_width = len(languages) * width + (len(languages) - 1) * gap
        start_x = (WINDOW_WIDTH - total_width) // 2
        return {
            language: pygame.Rect(start_x + index * (width + gap), 505, width, 42)
            for index, language in enumerate(languages)
        }

    @staticmethod
    def finish_setup_rect() -> pygame.Rect:
        return pygame.Rect(SIDEBAR_X + 56, 694, SIDEBAR_WIDTH - 112, 55)

    @staticmethod
    def king_choice_rects() -> dict[Game, pygame.Rect]:
        return {
            "xiangqi": pygame.Rect(SIDEBAR_X + 130, 142, 166, 34),
            "chess": pygame.Rect(SIDEBAR_X + 304, 142, 188, 34),
        }

    @staticmethod
    def handoff_button_rect() -> pygame.Rect:
        return pygame.Rect(WINDOW_WIDTH // 2 - 155, 490, 310, 66)

    @staticmethod
    def catalog_rects() -> dict[int, pygame.Rect]:
        rects = {}
        item_width, item_height = 145, 50
        start_x, start_y = SIDEBAR_X + 24, 238
        visible_index = 0
        for catalog_index, item in enumerate(PIECE_CATALOG):
            if item["limit"] == 0:
                continue
            col, row = visible_index % 3, visible_index // 3
            rects[catalog_index] = pygame.Rect(
                start_x + col * (item_width + 10),
                start_y + row * (item_height + 8),
                item_width,
                item_height,
            )
            visible_index += 1
        return rects

    @staticmethod
    def promotion_rects() -> dict[str, pygame.Rect]:
        kinds = ("queen", "rook", "bishop", "knight")
        item_width, gap = 125, 10
        total_width = len(kinds) * item_width + (len(kinds) - 1) * gap
        start_x = (WINDOW_WIDTH - total_width) // 2
        return {
            kind: pygame.Rect(start_x + index * (item_width + gap), 396, item_width, 82)
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
        for game_mode, rect in self.game_mode_rects().items():
            self.draw_button(
                rect,
                self.tr(f"menu.mode.{game_mode}"),
                active=game_mode == self.game_mode,
            )
        self.draw_button(
            self.menu_start_rect(),
            self.tr(f"menu.start.{self.game_mode}"),
            active=True,
        )
        self.draw_text(
            self.tr("menu.tagline"),
            self.fonts["small"],
            COLORS["muted"],
            (640, 660),
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
            king = self.kings[self.setup_side]
            selecting_general = self.selected_setup_king and king.game == "xiangqi"
            rows = (
                [7, 8, 9]
                if selecting_general and self.setup_side == "red"
                else [0, 1, 2]
                if selecting_general
                else sorted(DEPLOYMENT_ROWS[self.setup_side])
            )
            columns = range(3, 6) if selecting_general else range(BOARD_COLS)
            top_y = self.board_to_pixel((0, rows[0]))[1] - GRID_SIZE // 2
            left_x = self.board_to_pixel((columns[0], 0))[0] - GRID_SIZE // 2
            width = (columns[-1] - columns[0] + 1) * GRID_SIZE
            height = (rows[-1] - rows[0] + 1) * GRID_SIZE
            highlight = pygame.Surface((width, height), pygame.SRCALPHA)
            team_color = TEAM_COLORS[self.setup_side]
            highlight.fill((*team_color, 34))
            self.screen.blit(highlight, (left_x, top_y))

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
        if self.selected_setup_king and self.state == "setup":
            pygame.draw.circle(
                self.screen,
                COLORS["selected"],
                self.board_to_pixel(self.kings[self.setup_side].position),
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

    def draw_piece(
        self, piece: Piece, center: PixelPosition, *, size: int = 48
    ) -> None:
        team_color = TEAM_COLORS[piece.side]
        image = self.images.get((piece.game, piece.kind, piece.side))
        if image is not None:
            scaled_image = pygame.transform.smoothscale(image, (size, size))
            self.screen.blit(scaled_image, scaled_image.get_rect(center=center))
            return

        radius = size // 2
        pygame.draw.circle(self.screen, (246, 229, 192), center, radius)
        pygame.draw.circle(self.screen, team_color, center, radius, 3)
        font = self.fonts["piece"] if size >= 44 else self.fonts["small"]
        self.draw_text(piece.label(), font, team_color, center, center=True)

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
        self.draw_king_selector()
        self.draw_text(
            self.tr("setup.instructions"),
            self.fonts["tiny"],
            COLORS["muted"],
            (SIDEBAR_X + 28, 184),
        )
        self.draw_text(
            self.tr("setup.shop"),
            self.fonts["body"],
            COLORS["text"],
            (SIDEBAR_X + 28, 207),
        )

        for index, rect in self.catalog_rects().items():
            item = PIECE_CATALOG[index]
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
            self.draw_piece(piece_sample, (rect.x + 24, rect.centery), size=38)
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
                (rect.x + 48, rect.y + 29),
            )

        preview_item = (
            PIECE_CATALOG[self.selected_catalog_index]
            if self.selected_catalog_index is not None
            else self.catalog_item_for(self.kings[self.setup_side])
            if self.selected_setup_king
            else None
        )
        if preview_item is not None:
            self.draw_movement_preview(preview_item)

        self.draw_text(
            self.status, self.fonts["small"], COLORS["muted"], (SIDEBAR_X + 28, 662)
        )
        king = self.kings[self.setup_side]
        self.draw_button(
            self.finish_setup_rect(),
            self.tr("setup.finish"),
            active=valid_king_setup_position(king, king.position),
        )

    def draw_king_selector(self) -> None:
        king = self.kings[self.setup_side]
        self.draw_text(
            self.tr("setup.king_label"),
            self.fonts["small"],
            COLORS["text"],
            (SIDEBAR_X + 28, 149),
        )
        for game, rect in self.king_choice_rects().items():
            selected = king.game == game
            affordable = (
                game == "xiangqi"
                or selected
                or self.budgets[self.setup_side] >= CHESS_KING_COST
            )
            fill = (255, 239, 189) if selected else COLORS["panel"]
            if not affordable:
                fill = (224, 220, 211)
            border = COLORS["selected"] if selected else (198, 191, 179)
            pygame.draw.rect(self.screen, fill, rect, border_radius=8)
            pygame.draw.rect(
                self.screen, border, rect, 3 if selected else 1, border_radius=8
            )
            text_color = COLORS["text"] if affordable else COLORS["muted"]
            self.draw_text(
                self.tr(f"setup.king.{game}"),
                self.fonts["tiny"],
                text_color,
                rect.center,
                center=True,
            )

    def draw_movement_preview(self, item: CatalogItem) -> None:
        """Draw localized movement help for the selected shop piece."""
        panel = pygame.Rect(SIDEBAR_X + 24, 468, SIDEBAR_WIDTH - 48, 180)
        pygame.draw.rect(self.screen, (244, 238, 224), panel, border_radius=10)
        pygame.draw.rect(self.screen, (198, 191, 179), panel, 1, border_radius=10)

        piece_name = self.catalog_item_name(item)
        self.draw_text(
            self.tr("setup.movement", piece=piece_name),
            self.fonts["small"],
            COLORS["text"],
            (panel.x + 14, panel.y + 11),
        )
        self.draw_wrapped_text(
            self.tr(f"movement.{item['game']}.{item['kind']}"),
            self.fonts["tiny"],
            COLORS["muted"],
            (panel.x + 14, panel.y + 43),
            max_width=220,
            line_height=19,
        )

        preview_key = (item["game"], item["kind"])
        if preview_key == ("xiangqi", "bing"):
            self.draw_xiangqi_soldier_preview(panel, item)
            return
        if preview_key == ("chess", "pawn"):
            self.draw_chess_pawn_preview(panel, item)
            return
        if preview_key == ("xiangqi", "king"):
            self.draw_general_preview(panel, item)
            return

        pattern = MOVEMENT_PREVIEWS[preview_key]
        center = (panel.x + 362, panel.y + 88)
        spacing = 27
        board_rect = pygame.Rect(center[0] - 66, center[1] - 66, 132, 132)
        pygame.draw.rect(self.screen, COLORS["board"], board_rect, border_radius=6)
        pygame.draw.rect(
            self.screen, COLORS["board_dark"], board_rect, 2, border_radius=6
        )
        for grid_offset in range(-2, 3):
            x = center[0] + grid_offset * spacing
            y = center[1] + grid_offset * spacing
            pygame.draw.line(
                self.screen,
                COLORS["board_dark"],
                (x, center[1] - 2 * spacing),
                (x, center[1] + 2 * spacing),
                1,
            )
            pygame.draw.line(
                self.screen,
                COLORS["board_dark"],
                (center[0] - 2 * spacing, y),
                (center[0] + 2 * spacing, y),
                1,
            )

        def preview_point(offset: BoardPosition) -> PixelPosition:
            dx, dy = offset
            if self.setup_side == "black":
                dy = -dy
            return center[0] + dx * spacing, center[1] + dy * spacing

        for move_offset in pattern.moves:
            pygame.draw.circle(
                self.screen, COLORS["move"], preview_point(move_offset), 5
            )
        for capture_offset in pattern.captures:
            pygame.draw.circle(
                self.screen, COLORS["capture"], preview_point(capture_offset), 9, 3
            )
        for blocker_offset in pattern.blockers:
            marker = pygame.Rect(0, 0, 9, 9)
            marker.center = preview_point(blocker_offset)
            pygame.draw.rect(self.screen, COLORS["muted"], marker, border_radius=2)

        sample = Piece(0, item["game"], item["kind"], self.setup_side, (0, 0))
        self.draw_piece(sample, center, size=34)
        self.draw_movement_legend((panel.x + 14, panel.bottom - 19), pattern)

    def draw_preview_grid(
        self,
        center: PixelPosition,
        *,
        columns: int,
        rows: int,
        spacing: int,
    ) -> None:
        """Draw a compact board centered on a preview diagram."""
        half_width = (columns - 1) * spacing // 2
        half_height = (rows - 1) * spacing // 2
        board_rect = pygame.Rect(
            center[0] - half_width - 8,
            center[1] - half_height - 8,
            half_width * 2 + 16,
            half_height * 2 + 16,
        )
        pygame.draw.rect(self.screen, COLORS["board"], board_rect, border_radius=5)
        pygame.draw.rect(
            self.screen, COLORS["board_dark"], board_rect, 2, border_radius=5
        )
        for column in range(columns):
            x = center[0] + (column - (columns - 1) // 2) * spacing
            pygame.draw.line(
                self.screen,
                COLORS["board_dark"],
                (x, center[1] - half_height),
                (x, center[1] + half_height),
                1,
            )
        for row in range(rows):
            y = center[1] + (row - (rows - 1) // 2) * spacing
            pygame.draw.line(
                self.screen,
                COLORS["board_dark"],
                (center[0] - half_width, y),
                (center[0] + half_width, y),
                1,
            )

    def oriented_preview_point(
        self,
        origin: PixelPosition,
        offset: BoardPosition,
        spacing: int,
    ) -> PixelPosition:
        dx, dy = offset
        if self.setup_side == "black":
            dy = -dy
        return origin[0] + dx * spacing, origin[1] + dy * spacing

    def draw_xiangqi_soldier_preview(
        self, panel: pygame.Rect, item: CatalogItem
    ) -> None:
        spacing = 23
        diagrams = (
            (panel.x + 299, self.tr("setup.preview.before_river"), ((0, -1),)),
            (
                panel.x + 410,
                self.tr("setup.preview.after_river"),
                ((0, -1), (-1, 0), (1, 0)),
            ),
        )
        for center_x, label, moves in diagrams:
            self.draw_wrapped_text(
                label,
                self.fonts["micro"],
                COLORS["muted"],
                (center_x, panel.y + 39),
                max_width=100,
                line_height=13,
                center=True,
            )
            center = (center_x, panel.y + 95)
            self.draw_preview_grid(center, columns=3, rows=3, spacing=spacing)
            for move in moves:
                pygame.draw.circle(
                    self.screen,
                    COLORS["move"],
                    self.oriented_preview_point(center, move, spacing),
                    5,
                )
            sample = Piece(0, item["game"], item["kind"], self.setup_side, (0, 0))
            self.draw_piece(sample, center, size=28)
        self.draw_movement_legend(
            (panel.x + 14, panel.bottom - 19), MovementPreview(((0, -1),))
        )

    def draw_chess_pawn_preview(self, panel: pygame.Rect, item: CatalogItem) -> None:
        spacing = 19
        first_center = (panel.x + 300, panel.y + 106)
        self.draw_wrapped_text(
            self.tr("setup.preview.first_move"),
            self.fonts["micro"],
            COLORS["muted"],
            (first_center[0], panel.y + 37),
            max_width=104,
            line_height=13,
            center=True,
        )
        self.draw_preview_grid(first_center, columns=3, rows=5, spacing=spacing)
        pawn_center = self.oriented_preview_point(first_center, (0, 1), spacing)
        one_step = self.oriented_preview_point(pawn_center, (0, -1), spacing)
        two_step = self.oriented_preview_point(pawn_center, (0, -2), spacing)
        pygame.draw.circle(self.screen, COLORS["move"], one_step, 5)
        pygame.draw.circle(self.screen, COLORS["move"], two_step, 5)
        pygame.draw.circle(self.screen, COLORS["selected"], two_step, 10, 3)
        for capture_offset in ((-1, -1), (1, -1)):
            pygame.draw.circle(
                self.screen,
                COLORS["capture"],
                self.oriented_preview_point(pawn_center, capture_offset, spacing),
                8,
                3,
            )
        pawn = Piece(0, item["game"], item["kind"], self.setup_side, (0, 0))
        self.draw_piece(pawn, pawn_center, size=26)

        promotion_center = (panel.x + 410, panel.y + 106)
        self.draw_wrapped_text(
            self.tr("setup.preview.last_row"),
            self.fonts["micro"],
            COLORS["muted"],
            (promotion_center[0], panel.y + 37),
            max_width=104,
            line_height=13,
            center=True,
        )
        self.draw_preview_grid(promotion_center, columns=5, rows=5, spacing=spacing)
        start_y = promotion_center[1] + (
            2 * spacing if self.setup_side == "red" else -2 * spacing
        )
        final_y = promotion_center[1] + (
            -2 * spacing if self.setup_side == "red" else 2 * spacing
        )
        pygame.draw.line(
            self.screen,
            COLORS["move"],
            (promotion_center[0], start_y),
            (promotion_center[0], final_y),
            3,
        )
        self.draw_piece(pawn, (promotion_center[0], start_y), size=22)
        for index, kind in enumerate(("queen", "rook", "bishop", "knight")):
            promoted = Piece(0, "chess", kind, self.setup_side, (0, 0))
            icon_x = promotion_center[0] + (index * 22) - 33
            self.draw_piece(promoted, (icon_x, final_y), size=20)

        pawn_pattern = MovementPreview(((0, -1), (0, -2)), captures=((-1, -1), (1, -1)))
        self.draw_movement_legend((panel.x + 14, panel.bottom - 19), pawn_pattern)
        double_step_marker = (panel.x + 305, panel.bottom - 13)
        pygame.draw.circle(self.screen, COLORS["selected"], double_step_marker, 6, 2)
        self.draw_text(
            self.tr("setup.preview.double_only"),
            self.fonts["micro"],
            COLORS["selected"],
            (double_step_marker[0] + 11, panel.bottom - 20),
        )

    def draw_general_preview(self, panel: pygame.Rect, item: CatalogItem) -> None:
        center = (panel.x + 362, panel.y + 88)
        spacing = 27
        self.draw_preview_grid(center, columns=5, rows=5, spacing=spacing)
        own_center = self.oriented_preview_point(center, (0, 1), spacing)
        enemy_center = self.oriented_preview_point(center, (0, -2), spacing)
        pygame.draw.line(self.screen, COLORS["accent"], own_center, enemy_center, 3)
        for move in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            pygame.draw.circle(
                self.screen,
                COLORS["move"],
                self.oriented_preview_point(own_center, move, spacing),
                5,
            )
        own_general = Piece(0, "xiangqi", "king", self.setup_side, (0, 0))
        enemy_general = Piece(0, "xiangqi", "king", own_general.enemy_side, (0, 0))
        self.draw_piece(enemy_general, enemy_center, size=28)
        self.draw_piece(own_general, own_center, size=30)
        self.draw_movement_legend(
            (panel.x + 14, panel.bottom - 19), MovementPreview(((0, -1),))
        )
        facing_label = f"OK: {self.tr('setup.preview.facing_allowed')}"
        self.draw_text(
            facing_label,
            self.fonts["micro"],
            COLORS["accent"],
            (panel.x + 344, panel.bottom - 21),
            center=True,
        )

    def draw_movement_legend(
        self, position: PixelPosition, pattern: MovementPreview
    ) -> None:
        legend = [("move", COLORS["move"])]
        if pattern.captures:
            legend.append(("capture", COLORS["capture"]))
        if pattern.blocker_label is not None:
            legend.append((pattern.blocker_label, COLORS["muted"]))

        x, y = position
        for kind, color in legend:
            if kind == "capture":
                pygame.draw.circle(self.screen, color, (x + 5, y + 6), 5, 2)
            elif kind in ("blocker", "screen"):
                pygame.draw.rect(
                    self.screen, color, pygame.Rect(x, y + 1, 10, 10), border_radius=2
                )
            else:
                pygame.draw.circle(self.screen, color, (x + 5, y + 6), 4)
            label = self.tr(f"setup.preview.{kind}")
            self.draw_text(
                label,
                self.fonts["tiny"],
                COLORS["muted"],
                (x + 14, y - 2),
            )
            x += self.fonts["tiny"].size(label)[0] + 32

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
        if self.game_mode == "single":
            self.draw_text(
                self.tr("play.ai_opponent"),
                self.fonts["small"],
                COLORS["accent"],
                (SIDEBAR_X + 28, 235),
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
        side = self.pending_promotion.side if self.pending_promotion else self.turn
        for kind, rect in self.promotion_rects().items():
            self.draw_button(rect, "", active=True)
            promoted = Piece(0, "chess", kind, side, (0, 0))
            self.draw_piece(promoted, (rect.centerx, rect.y + 30), size=42)
            self.draw_text(
                self.tr(f"piece.chess.{kind}"),
                self.fonts["micro"],
                COLORS["white"],
                (rect.centerx, rect.bottom - 14),
                center=True,
            )

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

    def draw_wrapped_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        position: PixelPosition,
        *,
        max_width: int,
        line_height: int,
        center: bool = False,
    ) -> None:
        """Draw text within a fixed width, including text without spaces."""
        separator = " " if " " in text else ""
        units = text.split(" ") if separator else list(text)
        lines: list[str] = []
        current = ""
        for unit in units:
            candidate = f"{current}{separator if current else ''}{unit}"
            if not current or font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            lines.append(current)
            current = unit
        if current:
            lines.append(current)

        x, y = position
        for line in lines:
            self.draw_text(line, font, color, (x, y), center=center)
            y += line_height

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
