# Chess Confluence rules reference

This file defines the rules implemented by the current engine. Movement previews
in the game are summaries; this document is the reference for edge cases and
terminal outcomes.

## Setup

- Each side starts with 40 points and may buy at most 20 non-leader pieces.
- Prices are displayed in 0.5-point increments. Internally, one integer unit is
  one half-point so purchases and refunds are exact.
- Per-kind limits and prices come from `PIECE_DEFINITIONS` in `settings.py`.
- A Xiangqi general is free and must be placed in its side's 3×3 palace.
- A chess king costs 3 additional points and may be placed anywhere in its
  side's four deployment rows.
- Other pieces may be placed anywhere in those four rows if the intersection is
  empty and the budget and purchase limits allow it.
- Purchased pieces can be removed for a full refund before battle begins.
- In single-player setup, the AI does not receive the human army's hidden
  positions, regardless of the selected side.

## Turn and movement rules

- Red moves first; turns then alternate one piece at a time.
- A piece uses the movement rules of its source game.
- Friendly pieces cannot be captured and, except for jumping pieces and cannon
  captures, pieces cannot move through occupied intersections.
- Moving into a position where the leader can be captured is legal. The UI may
  display “check” as a warning, but check does not restrict the action set.
- There is no checkmate, castling, or en passant.
- A chess pawn's two-step move depends on its own `moved` flag rather than its
  current row. On reaching the last row, it must promote before the turn ends.
- A Xiangqi soldier gains sideways movement after crossing the river and never
  retreats.
- Xiangqi horse-leg, elephant-eye, and cannon-screen blocking rules apply.
- Xiangqi elephants and advisors may leave their traditional zones in this
  variant. Generals remain inside their palaces, but may face each other on an
  open file.

## Terminal outcomes

Automatic terminal rules are evaluated in this order:

1. Capturing the opposing leader wins immediately.
2. At the start of a turn, a side with no legal action loses by immobilization.
3. The third occurrence of the same position is a draw.
4. The game is a draw after 100 consecutive plies without a capture or a
   pawn/soldier move.

A resignation is an explicit action rather than an automatic adjudication; it
immediately awards the game to the opposing side.

A *ply* is one side's action. Captures and chess-pawn or Xiangqi-soldier moves
reset the no-progress counter.

For repetition, a position contains the side to move and every piece's source
game, kind, side, and coordinate. A chess pawn's `moved` flag is also included
because it changes that pawn's legal action set. Piece identifiers and irrelevant
`moved` flags do not distinguish positions.

Promotion is part of the pawn's action. A human promotion pauses the interface
for a choice without changing turns; AI promotion is supplied with its move.
The provisional move is recorded immediately and completed with the selected
piece; repetition and terminal checks wait until the promotion is complete.
