"""JSON-compatible match records used for replay, undo, and datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from pieces import BoardPosition, Game, Piece, Side

RECORD_FORMAT = "chess-confluence-match"
RECORD_VERSION = 1
ActionKind = Literal["move", "resign"]
MetadataValue = str | int | bool | None


class MatchRecordError(ValueError):
    """Raised when external match data has an invalid or unsupported shape."""


@dataclass(frozen=True)
class SetupPieceRecord:
    """One piece in the completed secret setup."""

    piece_id: int
    game: Game
    kind: str
    side: Side
    position: BoardPosition

    @classmethod
    def from_piece(cls, piece: Piece) -> SetupPieceRecord:
        return cls(piece.piece_id, piece.game, piece.kind, piece.side, piece.position)

    def to_dict(self) -> dict[str, object]:
        return {
            "piece_id": self.piece_id,
            "game": self.game,
            "kind": self.kind,
            "side": self.side,
            "position": list(self.position),
        }

    @classmethod
    def from_dict(cls, data: object) -> SetupPieceRecord:
        mapping = _mapping(data, "setup piece")
        return cls(
            _integer(mapping.get("piece_id"), "piece_id"),
            _game(mapping.get("game")),
            _string(mapping.get("kind"), "kind"),
            _side(mapping.get("side")),
            _position(mapping.get("position")),
        )


@dataclass(frozen=True)
class ActionRecord:
    """One complete move or resignation in chronological order."""

    kind: ActionKind
    side: Side
    piece_id: int | None = None
    origin: BoardPosition | None = None
    target: BoardPosition | None = None
    promotion: str | None = None
    captured_piece_id: int | None = None

    @classmethod
    def move(
        cls,
        side: Side,
        piece_id: int,
        origin: BoardPosition,
        target: BoardPosition,
        promotion: str | None,
        captured_piece_id: int | None,
    ) -> ActionRecord:
        return cls(
            "move",
            side,
            piece_id,
            origin,
            target,
            promotion,
            captured_piece_id,
        )

    @classmethod
    def resignation(cls, side: Side) -> ActionRecord:
        return cls("resign", side)

    def with_promotion(self, promotion: str) -> ActionRecord:
        if self.kind != "move":
            raise MatchRecordError("only a move can contain a promotion")
        return ActionRecord(
            self.kind,
            self.side,
            self.piece_id,
            self.origin,
            self.target,
            promotion,
            self.captured_piece_id,
        )

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"type": self.kind, "side": self.side}
        if self.kind == "move":
            data.update(
                {
                    "piece_id": self.piece_id,
                    "from": list(cast(BoardPosition, self.origin)),
                    "to": list(cast(BoardPosition, self.target)),
                    "promotion": self.promotion,
                    "captured_piece_id": self.captured_piece_id,
                }
            )
        return data

    @classmethod
    def from_dict(cls, data: object) -> ActionRecord:
        mapping = _mapping(data, "action")
        action_type = mapping.get("type")
        side = _side(mapping.get("side"))
        if action_type == "resign":
            return cls.resignation(side)
        if action_type != "move":
            raise MatchRecordError("action type must be 'move' or 'resign'")
        promotion_value = mapping.get("promotion")
        captured_value = mapping.get("captured_piece_id")
        return cls.move(
            side,
            _integer(mapping.get("piece_id"), "piece_id"),
            _position(mapping.get("from")),
            _position(mapping.get("to")),
            None if promotion_value is None else _string(promotion_value, "promotion"),
            None
            if captured_value is None
            else _integer(captured_value, "captured_piece_id"),
        )


@dataclass(frozen=True)
class ResultRecord:
    """Serializable terminal outcome."""

    winner: Side | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {"winner": self.winner, "reason": self.reason}

    @classmethod
    def from_dict(cls, data: object) -> ResultRecord:
        mapping = _mapping(data, "result")
        winner_value = mapping.get("winner")
        winner = None if winner_value is None else _side(winner_value)
        return cls(winner, _string(mapping.get("reason"), "reason"))


@dataclass
class MatchRecord:
    """Complete portable record of one match."""

    setup: tuple[SetupPieceRecord, ...] = ()
    actions: list[ActionRecord] = field(default_factory=list)
    result: ResultRecord | None = None
    metadata: dict[str, MetadataValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a structure accepted directly by :func:`json.dumps`."""
        return {
            "format": RECORD_FORMAT,
            "version": RECORD_VERSION,
            "metadata": dict(self.metadata),
            "setup": [piece.to_dict() for piece in self.setup],
            "actions": [action.to_dict() for action in self.actions],
            "result": None if self.result is None else self.result.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: object) -> MatchRecord:
        mapping = _mapping(data, "match record")
        if mapping.get("format") != RECORD_FORMAT:
            raise MatchRecordError("unsupported match record format")
        if mapping.get("version") != RECORD_VERSION:
            raise MatchRecordError("unsupported match record version")
        setup_value = mapping.get("setup")
        actions_value = mapping.get("actions")
        if not isinstance(setup_value, list) or not isinstance(actions_value, list):
            raise MatchRecordError("setup and actions must be arrays")
        metadata_value = _mapping(mapping.get("metadata", {}), "metadata")
        metadata: dict[str, MetadataValue] = {}
        for key, value in metadata_value.items():
            if not isinstance(key, str) or not (
                value is None or isinstance(value, str | int | bool)
            ):
                raise MatchRecordError("metadata must contain JSON scalar values")
            metadata[key] = value
        result_value = mapping.get("result")
        return cls(
            tuple(SetupPieceRecord.from_dict(item) for item in setup_value),
            [ActionRecord.from_dict(item) for item in actions_value],
            None if result_value is None else ResultRecord.from_dict(result_value),
            metadata,
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, text: str) -> MatchRecord:
        try:
            data: Any = json.loads(text)
        except json.JSONDecodeError as error:
            raise MatchRecordError("invalid match record JSON") from error
        return cls.from_dict(data)

    def save(self, path: str | Path) -> None:
        """Write UTF-8 JSON, creating only the requested parent directory."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> MatchRecord:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MatchRecordError(f"{label} must be an object")
    return cast(dict[str, Any], value)


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise MatchRecordError(f"{label} must be a non-empty string")
    return value


def _integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise MatchRecordError(f"{label} must be an integer")
    return value


def _side(value: object) -> Side:
    if value not in ("red", "black"):
        raise MatchRecordError("side must be 'red' or 'black'")
    return cast(Side, value)


def _game(value: object) -> Game:
    if value not in ("chess", "xiangqi"):
        raise MatchRecordError("game must be 'chess' or 'xiangqi'")
    return cast(Game, value)


def _position(value: object) -> BoardPosition:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(
            isinstance(item, int) and not isinstance(item, bool) for item in value
        )
    ):
        raise MatchRecordError("position must contain two integers")
    return cast(BoardPosition, (value[0], value[1]))
