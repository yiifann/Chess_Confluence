"""Tests for movement rules shared by the game and its UI."""

from pieces import Piece, legal_moves, valid_king_setup_position


def test_xiangqi_horse_is_blocked_at_its_leg() -> None:
    horse = Piece(1, "xiangqi", "horse", "red", (4, 4))
    blocker = Piece(2, "chess", "pawn", "red", (5, 4))

    moves = legal_moves(horse, [horse, blocker])

    assert (6, 3) not in moves
    assert (6, 5) not in moves
    assert (3, 2) in moves


def test_xiangqi_cannon_needs_exactly_one_screen_to_capture() -> None:
    cannon = Piece(1, "xiangqi", "cannon", "red", (0, 0))
    screen = Piece(2, "chess", "pawn", "red", (0, 2))
    target = Piece(3, "chess", "rook", "black", (0, 4))
    piece_behind_target = Piece(4, "chess", "queen", "black", (0, 6))

    moves = legal_moves(cannon, [cannon, screen, target, piece_behind_target])

    assert (0, 1) in moves
    assert (0, 3) not in moves
    assert (0, 4) in moves
    assert (0, 6) not in moves


def test_chess_pawn_can_only_move_two_steps_before_its_first_move() -> None:
    pawn = Piece(1, "chess", "pawn", "red", (4, 6))

    assert legal_moves(pawn, [pawn]) == [(4, 5), (4, 4)]

    pawn.moved = True
    assert legal_moves(pawn, [pawn]) == [(4, 5)]


def test_chess_king_moves_one_step_in_any_direction() -> None:
    king = Piece(1, "chess", "king", "red", (4, 4))
    friendly_piece = Piece(2, "chess", "pawn", "red", (3, 3))
    enemy_piece = Piece(3, "chess", "pawn", "black", (5, 5))

    moves = set(legal_moves(king, [king, friendly_piece, enemy_piece]))

    assert (3, 3) not in moves
    assert (5, 5) in moves
    assert moves == {
        (4, 3),
        (5, 3),
        (3, 4),
        (5, 4),
        (3, 5),
        (4, 5),
        (5, 5),
    }


def test_kings_have_different_secret_setup_zones() -> None:
    general = Piece(1, "xiangqi", "king", "red", (4, 9))
    chess_king = Piece(2, "chess", "king", "red", (4, 9))

    assert valid_king_setup_position(general, (3, 7))
    assert valid_king_setup_position(general, (5, 9))
    assert not valid_king_setup_position(general, (2, 7))
    assert not valid_king_setup_position(general, (4, 6))

    assert valid_king_setup_position(chess_king, (0, 6))
    assert valid_king_setup_position(chess_king, (8, 9))
    assert not valid_king_setup_position(chess_king, (4, 5))
    assert not valid_king_setup_position(chess_king, (9, 9))


def test_advisor_is_not_restricted_to_the_palace() -> None:
    advisor = Piece(1, "xiangqi", "advisor", "red", (2, 4))

    assert set(legal_moves(advisor, [advisor])) == {
        (1, 3),
        (1, 5),
        (3, 3),
        (3, 5),
    }


def test_elephant_can_cross_the_river_but_cannot_jump_its_eye() -> None:
    elephant = Piece(1, "xiangqi", "elephant", "red", (4, 5))
    blocker = Piece(2, "chess", "pawn", "red", (5, 4))

    moves = legal_moves(elephant, [elephant, blocker])

    assert (2, 3) in moves
    assert (6, 3) not in moves
