from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable

from rts_engine.core.types import PlayerId, Tick, UnitId


class CommandType(StrEnum):
    MOVE = "MOVE"


@dataclass(frozen=True, slots=True)
class Command:
    type: CommandType
    player_id: PlayerId
    sequence: int
    units: tuple[UnitId, ...] = field(default_factory=tuple)
    x: int | None = None
    y: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "units", tuple(sorted(self.units)))

    @property
    def sort_key(self) -> tuple[str, int, str, tuple[int, ...], int]:
        return (
            str(self.player_id),
            self.sequence,
            self.type.value,
            tuple(int(unit_id) for unit_id in self.units),
            int(self.x or 0) ^ int(self.y or 0),
        )

    def to_wire(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type.value,
            "player_id": str(self.player_id),
            "sequence": self.sequence,
        }
        if self.units:
            data["units"] = [int(unit_id) for unit_id in self.units]
        if self.x is not None:
            data["x"] = self.x
        if self.y is not None:
            data["y"] = self.y
        return data

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> Command:
        return cls(
            type=CommandType(data["type"]),
            player_id=PlayerId(data["player_id"]),
            sequence=int(data["sequence"]),
            units=tuple(UnitId(int(unit_id)) for unit_id in data.get("units", ())),
            x=int(data["x"]) if "x" in data else None,
            y=int(data["y"]) if "y" in data else None,
        )


@dataclass(frozen=True, slots=True)
class CommandFrame:
    tick: Tick
    commands: tuple[Command, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "commands", tuple(sorted(self.commands, key=lambda command: command.sort_key)))

    def to_wire(self) -> dict[str, Any]:
        return {
            "kind": "command_frame",
            "tick": int(self.tick),
            "commands": [command.to_wire() for command in self.commands],
        }

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> CommandFrame:
        return cls(
            tick=Tick(int(data["tick"])),
            commands=tuple(Command.from_wire(command) for command in data.get("commands", ())),
        )


def canonical_commands(commands: Iterable[Command]) -> tuple[Command, ...]:
    return tuple(sorted(commands, key=lambda command: command.sort_key))
