"""Headless tests for single-player option and rematch orchestration."""

import sys
from types import ModuleType

# The controller logic under test does not render. CI separately installs and
# imports real Pygame, while this keeps the unit suite runnable without SDL.
sys.modules.setdefault("pygame", ModuleType("pygame"))

from ai import HeuristicPolicy  # noqa: E402
from engine import GameEngine  # noqa: E402
from main import HybridChessGame  # noqa: E402
from settings import PIECE_DEFINITION_BY_KEY  # noqa: E402


def controller() -> HybridChessGame:
    game = HybridChessGame.__new__(HybridChessGame)
    game.language = "en"
    game.game_mode = "single"
    game.human_side = "red"
    game.ai_difficulty = "medium"
    game.deterministic_ai_setup = False
    game.show_setup_after_match = True
    game.custom_ai_policy = False
    game.ai_policy = HeuristicPolicy(seed=1)
    game.engine = GameEngine()
    game.state = "menu"
    game.replay_record = None
    game.replay_index = 0
    game.reset_match()
    return game


def side_setup(game: HybridChessGame, side: str) -> tuple[object, ...]:
    return tuple(
        (piece.game, piece.kind, piece.position)
        for piece in sorted(game.pieces, key=lambda item: item.piece_id)
        if piece.side == side
    )


def test_human_can_choose_black_and_ai_secretly_builds_red_first() -> None:
    game = controller()
    game.human_side = "black"
    game.ai_difficulty = "hard"
    game.deterministic_ai_setup = True

    game.start_new_match()
    first_red_setup = side_setup(game, "red")

    assert game.setup_side == "black"
    assert game.state == "setup"
    assert game.bought_totals["red"] > 0
    assert game.bought_totals["black"] == 0
    assert isinstance(game.ai_policy, HeuristicPolicy)
    assert game.ai_policy.difficulty == "hard"

    game.start_new_match()
    assert side_setup(game, "red") == first_red_setup

    game.finish_setup()
    assert game.state == "playing"
    assert game.turn == "red"
    assert game.engine.record.metadata["human_side"] == "black"


def test_same_army_rematch_reuses_exact_setup_and_clears_actions() -> None:
    game = controller()
    game.deterministic_ai_setup = True
    game.start_new_match()
    game.finish_setup()
    original_setup = game.engine.record.setup
    game.engine.resign("red")

    game.rematch_same_armies()

    assert game.state == "playing"
    assert game.engine.record.setup == original_setup
    assert game.engine.record.actions == []
    assert game.engine.state.result is None


def test_new_ai_rematch_keeps_the_human_army() -> None:
    game = controller()
    game.start_new_match()
    advisor = PIECE_DEFINITION_BY_KEY[("xiangqi", "advisor")]
    assert game.engine.buy_piece("red", advisor, (3, 8)).accepted
    game.finish_setup()
    human_setup = side_setup(game, "red")
    game.engine.resign("red")

    game.rematch_new_ai_army()

    assert game.state == "playing"
    assert side_setup(game, "red") == human_setup
    assert game.bought_totals["black"] > 0
    assert game.engine.record.actions == []
