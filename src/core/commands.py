from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable

from core.types import EntityId, Tick


class CommandType(StrEnum):
    MOVE = "MOVE"


@dataclass(frozen=True, slots=True)
class Command:
    type: CommandType
    issuer: EntityId
    sequence: int
    targets: tuple[EntityId, ...] = field(default_factory=tuple)
    x: int | None = None
    y: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "targets", tuple(sorted(self.targets, key=int)))

    @property
    def sort_key(self) -> tuple[int, int, str, tuple[int, ...], int]:
        return (
            int(self.issuer),
            self.sequence,
            self.type.value,
            tuple(int(entity_id) for entity_id in self.targets),
            int(self.x or 0) ^ int(self.y or 0),
        )

    def to_wire(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type.value,
            "issuer": int(self.issuer),
            "sequence": self.sequence,
        }
        if self.targets:
            data["targets"] = [int(entity_id) for entity_id in self.targets]
        if self.x is not None:
            data["x"] = self.x
        if self.y is not None:
            data["y"] = self.y
        return data

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> Command:
        return cls(
            type=CommandType(data["type"]),
            issuer=EntityId(int(data["issuer"])),
            sequence=int(data["sequence"]),
            targets=tuple(
                EntityId(int(entity_id)) for entity_id in data.get("targets", ())
            ),
            x=int(data["x"]) if "x" in data else None,
            y=int(data["y"]) if "y" in data else None,
        )


@dataclass(frozen=True, slots=True)
class CommandFrame:
    tick: Tick
    commands: tuple[Command, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "commands",
            tuple(sorted(self.commands, key=lambda command: command.sort_key)),
        )

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
            commands=tuple(
                Command.from_wire(command) for command in data.get("commands", ())
            ),
        )


def canonical_commands(commands: Iterable[Command]) -> tuple[Command, ...]:
    return tuple(sorted(commands, key=lambda command: command.sort_key))
