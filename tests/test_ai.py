"""Tests for the renderer-independent AI policy contract."""

from collections import Counter

from ai import (
    CatalogOption,
    GameObservation,
    HeuristicPolicy,
    SetupRequest,
    enumerate_legal_actions,
)
from pieces import Piece, Side, valid_king_setup_position
from settings import (
    BOARD_COLS,
    BOARD_ROWS,
    CHESS_KING_COST,
    DEPLOYMENT_ROWS,
    MAX_BOUGHT_PIECES,
    PIECE_CATALOG,
    STARTING_BUDGET,
)


def observation(pieces: list[Piece], turn: Side = "black") -> GameObservation:
    return GameObservation.from_pieces(turn, pieces, BOARD_COLS, BOARD_ROWS)


def test_heuristic_setup_respects_budget_limits_and_deployment_zone() -> None:
    request = SetupRequest(
        side="black",
        budget=STARTING_BUDGET,
        max_pieces=MAX_BOUGHT_PIECES,
        catalog=tuple(
            CatalogOption(item["game"], item["kind"], item["cost"], item["limit"])
            for item in PIECE_CATALOG
            if item["limit"]
        ),
        deployment_rows=tuple(sorted(DEPLOYMENT_ROWS["black"])),
        occupied=((4, 9),),
        chess_king_cost=CHESS_KING_COST,
        board_columns=BOARD_COLS,
        board_rows=BOARD_ROWS,
    )

    plan = HeuristicPolicy(seed=7).choose_setup(request)

    king = Piece(1, plan.king_game, "king", "black", plan.king_position)
    assert valid_king_setup_position(king, plan.king_position)
    positions = [plan.king_position, *(item.position for item in plan.placements)]
    assert len(positions) == len(set(positions))
    assert all(item.position[1] in DEPLOYMENT_ROWS["black"] for item in plan.placements)

    option_by_key = {(option.game, option.kind): option for option in request.catalog}
    counts = Counter((item.game, item.kind) for item in plan.placements)
    assert all(count <= option_by_key[key].limit for key, count in counts.items())
    total_cost = sum(
        option_by_key[(item.game, item.kind)].cost for item in plan.placements
    ) + (CHESS_KING_COST if plan.king_game == "chess" else 0)
    assert total_cost <= STARTING_BUDGET
    assert len(plan.placements) <= MAX_BOUGHT_PIECES


def test_action_enumeration_only_returns_legal_moves_for_requested_side() -> None:
    black_rook = Piece(1, "chess", "rook", "black", (0, 0))
    black_king = Piece(2, "xiangqi", "king", "black", (4, 0))
    red_king = Piece(3, "xiangqi", "king", "red", (4, 9))
    state = observation([black_rook, black_king, red_king])

    actions = enumerate_legal_actions(state, "black")

    assert actions
    assert {action.piece_id for action in actions} <= {1, 2}
    assert len(actions) == len(set(actions))


def test_heuristic_ai_takes_an_available_king_capture() -> None:
    black_rook = Piece(1, "chess", "rook", "black", (0, 1))
    black_king = Piece(2, "xiangqi", "king", "black", (4, 0))
    red_king = Piece(3, "xiangqi", "king", "red", (0, 4))
    state = observation([black_rook, black_king, red_king])
    actions = enumerate_legal_actions(state, "black")

    chosen = HeuristicPolicy(seed=3).choose_move(state, actions)

    assert chosen is not None
    assert chosen.piece_id == black_rook.piece_id
    assert chosen.target == red_king.position


def test_heuristic_ai_promotes_to_queen() -> None:
    pawn = Piece(1, "chess", "pawn", "black", (2, 8), moved=True)
    state = observation(
        [
            pawn,
            Piece(2, "xiangqi", "king", "black", (4, 0)),
            Piece(3, "xiangqi", "king", "red", (4, 9)),
        ]
    )

    choice = HeuristicPolicy(seed=1).choose_promotion(
        state,
        state.pieces[0],
        ("queen", "rook", "bishop", "knight"),
    )

    assert choice == "queen"
