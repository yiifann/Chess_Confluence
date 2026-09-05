"""Consistency tests for canonical piece metadata."""

import pytest

from settings import PIECE_DEFINITION_BY_KEY, PIECE_DEFINITIONS, format_points


def test_piece_definitions_have_unique_keys_and_complete_assets() -> None:
    keys = [(definition.game, definition.kind) for definition in PIECE_DEFINITIONS]

    assert len(keys) == len(set(keys)) == len(PIECE_DEFINITION_BY_KEY)
    assert all(
        set(definition.images) == {"red", "black"} for definition in PIECE_DEFINITIONS
    )


def test_piece_definitions_are_the_single_source_for_cost_and_ai_value() -> None:
    purchasable = [definition for definition in PIECE_DEFINITIONS if definition.limit]
    leaders = [definition for definition in PIECE_DEFINITIONS if not definition.limit]

    assert all(definition.cost_units > 0 for definition in purchasable)
    assert all(definition.value_units > 0 for definition in PIECE_DEFINITIONS)
    assert all(
        definition.value_units >= definition.cost_units for definition in leaders
    )
    assert all(
        isinstance(definition.cost_units, int)
        and isinstance(definition.value_units, int)
        for definition in PIECE_DEFINITIONS
    )


@pytest.mark.parametrize(
    ("units", "display"),
    ((-1, "-0.5"), (0, "0"), (2, "1"), (3, "1.5"), (9, "4.5"), (80, "40")),
)
def test_half_point_units_have_stable_player_facing_format(
    units: int,
    display: str,
) -> None:
    assert format_points(units) == display
