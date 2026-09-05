"""Tests for authoritative setup, mutation, and terminal-state rules."""

import pytest

from engine import GameEngine, IllegalAction
from pieces import Piece, Side
from settings import (
    CHESS_KING_COST_UNITS,
    PIECE_DEFINITION_BY_KEY,
    STARTING_BUDGET_UNITS,
)


def battle_with(pieces: list[Piece], turn: Side = "red") -> GameEngine:
    """Create a compact battle fixture while preserving leader identity."""
    engine = GameEngine()
    engine.state.pieces = pieces
    engine.state.kings = {
        "red": next(
            piece for piece in pieces if piece.side == "red" and piece.kind == "king"
        ),
        "black": next(
            piece for piece in pieces if piece.side == "black" and piece.kind == "king"
        ),
    }
    engine.state.turn = turn
    engine.state.phase = "playing"
    engine.state.result = None
    engine.state.repetition_counts = {}
    return engine


def test_setup_mutations_enforce_zone_budget_and_refunds() -> None:
    engine = GameEngine()
    advisor = PIECE_DEFINITION_BY_KEY[("xiangqi", "advisor")]

    outside = engine.buy_piece("red", advisor, (4, 5))
    assert not outside.accepted
    assert outside.failure == "invalid_position"
    assert engine.state.budget_units["red"] == STARTING_BUDGET_UNITS

    bought = engine.buy_piece("red", advisor, (4, 6))
    assert bought.accepted
    assert (
        engine.state.budget_units["red"] == STARTING_BUDGET_UNITS - advisor.cost_units
    )

    removed = engine.remove_setup_piece("red", (4, 6))
    assert removed.accepted
    assert removed.cost_units == advisor.cost_units
    assert engine.state.budget_units["red"] == STARTING_BUDGET_UNITS


def test_chess_king_upgrade_and_refund_are_owned_by_engine() -> None:
    engine = GameEngine()

    assert engine.set_king_type("red", "chess").accepted
    assert (
        engine.state.budget_units["red"]
        == STARTING_BUDGET_UNITS - CHESS_KING_COST_UNITS
    )
    assert engine.set_king_type("red", "xiangqi").accepted
    assert engine.state.budget_units["red"] == STARTING_BUDGET_UNITS


def test_setup_cannot_be_mutated_after_battle_starts() -> None:
    engine = GameEngine()
    pawn = PIECE_DEFINITION_BY_KEY[("chess", "pawn")]
    assert engine.start_battle() is None

    outcome = engine.buy_piece("red", pawn, (0, 6))

    assert not outcome.accepted
    assert outcome.failure == "wrong_phase"
    assert engine.piece_at((0, 6)) is None


def test_king_capture_ends_the_match() -> None:
    red_king = Piece(1, "chess", "king", "red", (4, 9))
    black_king = Piece(2, "chess", "king", "black", (0, 4))
    rook = Piece(3, "chess", "rook", "red", (0, 1))
    engine = battle_with([red_king, black_king, rook])

    outcome = engine.apply_action(rook.piece_id, black_king.position)

    assert outcome.result is not None
    assert outcome.result.winner == "red"
    assert outcome.result.reason == "king_capture"


def test_moving_leader_into_attack_remains_legal_in_this_variant() -> None:
    red_king = Piece(1, "xiangqi", "king", "red", (4, 9))
    black_king = Piece(2, "xiangqi", "king", "black", (3, 0))
    black_rook = Piece(3, "chess", "rook", "black", (4, 0))
    engine = battle_with([red_king, black_king, black_rook])

    outcome = engine.apply_action(red_king.piece_id, (4, 8))

    assert outcome.result is None
    assert red_king.position == (4, 8)
    assert engine.is_in_check("red")


def test_side_with_no_legal_move_loses_in_every_game_mode() -> None:
    red_king = Piece(1, "xiangqi", "king", "red", (4, 9))
    black_king = Piece(2, "xiangqi", "king", "black", (4, 0))
    blockers = [
        Piece(3, "xiangqi", "wall", "black", (3, 0)),
        Piece(4, "xiangqi", "wall", "black", (5, 0)),
        Piece(5, "xiangqi", "wall", "black", (4, 1)),
    ]
    engine = battle_with([red_king, black_king, *blockers], turn="black")

    result = engine.adjudicate_current_turn()

    assert result is not None
    assert result.winner == "red"
    assert result.reason == "no_legal_moves"


def test_third_repetition_is_a_draw() -> None:
    red_king = Piece(1, "xiangqi", "king", "red", (4, 9))
    black_king = Piece(2, "xiangqi", "king", "black", (4, 0))
    engine = battle_with([red_king, black_king])
    assert engine.start_battle() is None

    cycle = (
        (red_king.piece_id, (3, 9)),
        (black_king.piece_id, (3, 0)),
        (red_king.piece_id, (4, 9)),
        (black_king.piece_id, (4, 0)),
    )
    outcome = None
    for _ in range(2):
        for piece_id, target in cycle:
            outcome = engine.apply_action(piece_id, target)

    assert outcome is not None and outcome.result is not None
    assert outcome.result.winner is None
    assert outcome.result.reason == "threefold_repetition"


def test_one_hundred_no_progress_plies_is_a_draw() -> None:
    red_king = Piece(1, "xiangqi", "king", "red", (4, 9))
    black_king = Piece(2, "xiangqi", "king", "black", (4, 0))
    engine = battle_with([red_king, black_king])
    assert engine.start_battle() is None
    engine.state.no_progress_plies = 99

    outcome = engine.apply_action(red_king.piece_id, (3, 9))

    assert outcome.result is not None
    assert outcome.result.winner is None
    assert outcome.result.reason == "move_limit"


def test_promotion_is_completed_before_the_turn_changes() -> None:
    pawn = Piece(3, "chess", "pawn", "red", (0, 1), moved=True)
    engine = battle_with(
        [
            Piece(1, "xiangqi", "king", "red", (4, 9)),
            Piece(2, "xiangqi", "king", "black", (4, 0)),
            pawn,
        ]
    )

    outcome = engine.apply_action(pawn.piece_id, (0, 0))
    assert outcome.promotion_required
    assert engine.state.turn == "red"
    assert engine.pending_promotion() is pawn

    promoted = engine.complete_promotion("queen")
    assert not promoted.promotion_required
    assert pawn.kind == "queen"
    assert engine.state.turn == "black"


def test_invalid_promotion_does_not_partially_apply_move() -> None:
    pawn = Piece(3, "chess", "pawn", "red", (0, 1), moved=True)
    engine = battle_with(
        [
            Piece(1, "xiangqi", "king", "red", (4, 9)),
            Piece(2, "xiangqi", "king", "black", (4, 0)),
            pawn,
        ]
    )

    with pytest.raises(IllegalAction):
        engine.apply_action(pawn.piece_id, (0, 0), promotion="dragon")

    assert pawn.position == (0, 1)
    assert engine.state.turn == "red"


def test_resignation_awards_the_game_to_the_opponent() -> None:
    engine = GameEngine()
    assert engine.start_battle() is None

    result = engine.resign("red")

    assert result.winner == "black"
    assert result.reason == "resignation"
    assert engine.state.phase == "game_over"
