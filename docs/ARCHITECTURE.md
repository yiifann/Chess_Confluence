# Chess Confluence architecture

This document describes the current demo's module boundaries, runtime flow, and
extension points. It is intended for contributors adding pieces, interfaces, or
AI policies.

## Module map

| Module | Responsibility |
|---|---|
| `main.py` | Pygame application, state transitions, input, rendering, and applying validated actions |
| `pieces.py` | Piece data model, board bounds, setup zones, and movement generation |
| `ai.py` | Renderer-independent policy contract, immutable observations/actions, and the heuristic AI |
| `settings.py` | Board geometry, colors, budgets, piece prices, limits, and asset paths |
| `i18n.py` | Chinese, English, and French UI message catalogs |
| `tests/` | Movement, localization, and AI policy regression tests |

The rules and AI modules deliberately do not import Pygame. This keeps them
usable in unit tests, headless simulations, and future training environments.

## Application state flow

```text
menu
  |
  v
red setup
  |-- single player --> AI setup --> playing
  |
  `-- local game --> privacy handoff --> black setup
                                      --> reveal handoff --> playing

playing --> promotion selection (human chess pawn only) --> playing
playing --> opposing king captured --> game over
game over --> new setup or menu
```

`HybridChessGame` owns the live mutable state. Event handlers select an action;
`execute_move()` is the common mutation path for both human and AI moves. This
ensures captures, promotion, win detection, and turn changes behave identically.

## Board and rule invariants

- Board coordinates are `(column, row)`, zero-based from the top-left.
- The board has 9 columns and 10 rows.
- Red advances toward decreasing row numbers; Black advances toward increasing
  row numbers.
- Every live piece has a unique `piece_id` and one occupied intersection.
- While both leaders are live, `pieces` contains the same objects referenced by
  `kings`.
- Costs use `float` values but are restricted by design to whole or half points.
- Victory is immediate capture of the opposing king/general. Checkmate,
  castling, en passant, and the Xiangqi flying-general rule are not part of this
  demo. If the AI has no legal action, it forfeits; local mode does not otherwise
  adjudicate stalemate.
- A Xiangqi general remains confined to its 3×3 palace. A chess king may be
  deployed anywhere in its side's four setup rows.

`legal_moves()` returns geometric moves under these project rules. It does not
remove moves that expose the moving side's leader, because leader capture—not
checkmate—is the win condition.

## AI boundary

`GamePolicy` is the only interface the Pygame controller expects from an AI. It
has three decisions:

1. `choose_setup(request)` returns the desired leader and purchased placements.
2. `choose_move(observation, legal_actions)` selects one supplied legal action.
3. `choose_promotion(observation, pawn, options)` selects a promotion kind.

The associated dataclasses are frozen and contain only ordinary Python values.
`GameObservation.from_pieces()` sorts snapshots by `piece_id`, and
`enumerate_legal_actions()` returns a deterministic ordering. These properties
make observation/action encoding repeatable for an RL adapter.

During secret setup, the Black policy receives the catalog and deployment rules
but not Red's piece positions. During play it receives the complete revealed
board. The controller validates setup placements, costs, limits, movement, and
promotion output before mutating live state. An invalid move falls back to the
first legal action rather than corrupting the match.

### Replacing the heuristic with an RL model

Implement the structural `GamePolicy` protocol and inject the instance:

```python
from ai import GameObservation, MoveAction, PieceView, SetupPlan, SetupRequest
from main import HybridChessGame


class RLPolicy:
    def choose_setup(self, request: SetupRequest) -> SetupPlan:
        observation = encode_setup(request)
        return decode_setup(model.predict(observation), request)

    def choose_move(
        self,
        observation: GameObservation,
        legal_actions: tuple[MoveAction, ...],
    ) -> MoveAction | None:
        if not legal_actions:
            return None
        features = encode_board(observation)
        mask = encode_action_mask(legal_actions)
        index = model.predict(features, mask)
        return legal_actions[index]

    def choose_promotion(
        self,
        observation: GameObservation,
        pawn: PieceView,
        options: tuple[str, ...],
    ) -> str:
        return options[model.predict_promotion(observation, pawn, options)]


HybridChessGame(ai_policy=RLPolicy()).run()
```

Keep model-specific tensors, devices, checkpoints, and dependencies inside the
adapter. The core policy types should remain framework-neutral.

## Common extensions

### Add or rebalance a piece

1. Update `PIECE_CATALOG` in `settings.py`.
2. Add or modify movement generation in `pieces.py`.
3. Add its movement preview and localized descriptions in `main.py` and
   `i18n.py`.
4. Update `PIECE_VALUES` and setup priorities in `ai.py`.
5. Add focused movement and AI tests.

### Add a language

1. Extend the `Language` literal and `LANGUAGE_LABELS` in `i18n.py`.
2. Add a complete translation dictionary with the same keys and placeholders.
3. Add the language to `HybridChessGame.language_rects()`.

`tests/test_i18n.py` verifies key and placeholder parity across every language.

## Verification

From the repository root:

```bash
python -m pytest -q -p no:cacheprovider
ruff check --no-cache main.py ai.py pieces.py settings.py i18n.py tests
ruff format --check --no-cache main.py ai.py pieces.py settings.py i18n.py tests
python -m mypy main.py ai.py pieces.py settings.py i18n.py tests \
  --ignore-missing-imports --cache-dir=NUL --no-error-summary
```

For rendering changes, also launch the game and inspect all three languages at
the configured 1280×800 window size.
