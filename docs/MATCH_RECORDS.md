# Match records and replay

`GameEngine` records the finalized secret setup and each battle action in a
versioned, JSON-compatible format. Records are suitable for replays, undo,
saved games, regression fixtures, reproducible bug reports, and AI datasets.

## Format

The top-level object contains:

- `format`: always `chess-confluence-match`;
- `version`: currently `1`;
- `metadata`: UI or experiment settings such as mode, side, and AI difficulty;
- `setup`: every initial piece with its stable ID, ruleset, side, and position;
- `actions`: ordered moves, promotions, captures, and resignations;
- `result`: the winner and terminal reason, or `null` for an unfinished match.

Coordinates are `[column, row]`, zero-based from the upper-left. Costs do not
need to be duplicated in a record because replay validates setup pieces against
the canonical catalog.

## Python API

```python
from engine import GameEngine
from match_history import MatchRecord

# JSON-compatible dictionary or UTF-8 JSON text
payload = engine.export_record()
text = engine.record.to_json()

# Explicit file save/load
engine.record.save("saves/example.json")
record = MatchRecord.load("saves/example.json")

# Validate and rebuild the entire match or a timeline prefix
finished = GameEngine.from_record(record)
after_five_actions = GameEngine.from_record(record, action_count=5)

# Rebuild the live engine before its last action
engine.undo_last_action()
```

Replay never trusts serialized board snapshots. It validates the setup and
reapplies actions through `GameEngine`, rejecting unknown pieces, invalid
budgets, impossible positions, illegal moves, incorrect captures, and results
that do not match the action sequence.

The game UI saves to `saves/last_match.json`. This runtime file is intentionally
ignored by Git.
