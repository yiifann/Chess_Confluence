"""Tests for portable match recording, replay, and undo."""

import json
from pathlib import Path

import pytest

from engine import GameEngine
from match_history import MatchRecord, MatchRecordError
from settings import PIECE_DEFINITION_BY_KEY


def test_record_is_json_compatible_and_replays_exact_position() -> None:
    engine = GameEngine()
    advisor = PIECE_DEFINITION_BY_KEY[("xiangqi", "advisor")]
    assert engine.buy_piece("red", advisor, (3, 8)).accepted
    assert engine.start_battle({"mode": "local", "deterministic": True}) is None

    red_king = engine.state.kings["red"]
    outcome = engine.apply_action(red_king.piece_id, (3, 9))
    assert outcome.result is None

    encoded = json.dumps(engine.export_record())
    decoded = MatchRecord.from_json(encoded)
    replayed = GameEngine.from_record(decoded)

    assert replayed.export_record() == engine.export_record()
    assert replayed.state.turn == engine.state.turn
    assert [
        (
            piece.piece_id,
            piece.game,
            piece.kind,
            piece.side,
            piece.position,
            piece.moved,
        )
        for piece in replayed.state.pieces
    ] == [
        (
            piece.piece_id,
            piece.game,
            piece.kind,
            piece.side,
            piece.position,
            piece.moved,
        )
        for piece in engine.state.pieces
    ]


def test_undo_rebuilds_draw_counters_and_board_from_history() -> None:
    engine = GameEngine()
    assert engine.start_battle() is None
    red_king = engine.state.kings["red"]
    engine.apply_action(red_king.piece_id, (3, 9))

    assert engine.undo_last_action()

    assert red_king.position != engine.state.kings["red"].position
    assert engine.state.kings["red"].position == (4, 9)
    assert engine.state.turn == "red"
    assert engine.state.no_progress_plies == 0
    assert engine.record.actions == []
    assert not engine.undo_last_action()


def test_promotion_and_resignation_are_recorded_as_actions() -> None:
    engine = GameEngine()
    pawn_definition = PIECE_DEFINITION_BY_KEY[("chess", "pawn")]
    purchase = engine.buy_piece("red", pawn_definition, (0, 6))
    assert purchase.accepted and purchase.piece is not None
    pawn = purchase.piece
    assert engine.start_battle() is None

    black_king = engine.state.kings["black"]
    for pawn_target, king_target in (
        ((0, 4), (3, 0)),
        ((0, 3), (4, 0)),
        ((0, 2), (3, 0)),
        ((0, 1), (4, 0)),
    ):
        engine.apply_action(pawn.piece_id, pawn_target)
        engine.apply_action(black_king.piece_id, king_target)

    pending = engine.apply_action(pawn.piece_id, (0, 0))
    assert pending.promotion_required
    assert engine.record.actions[-1].promotion is None
    engine.complete_promotion("queen")
    assert engine.record.actions[-1].promotion == "queen"
    engine.resign("black")

    replayed = GameEngine.from_record(engine.record)

    assert replayed.state.result == engine.state.result
    assert replayed.state.result is not None
    assert replayed.state.result.reason == "resignation"


def test_replay_rejects_tampered_action() -> None:
    engine = GameEngine()
    assert engine.start_battle() is None
    red_king = engine.state.kings["red"]
    engine.apply_action(red_king.piece_id, (3, 9))
    data = engine.export_record()
    actions = data["actions"]
    assert isinstance(actions, list)
    action = actions[0]
    assert isinstance(action, dict)
    action["to"] = [8, 8]

    with pytest.raises(MatchRecordError):
        GameEngine.from_record(data)


def test_record_can_be_saved_and_loaded_as_utf8_json(tmp_path: Path) -> None:
    engine = GameEngine()
    assert engine.start_battle({"label": "测试 · replay"}) is None
    destination = tmp_path / "nested" / "match.json"

    engine.record.save(destination)
    loaded = MatchRecord.load(destination)

    assert loaded.to_dict() == engine.record.to_dict()
    assert json.loads(destination.read_text(encoding="utf-8"))["version"] == 1
