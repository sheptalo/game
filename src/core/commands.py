from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Iterable, Self

from core.types import EntityId, Tick


@dataclass(frozen=True, slots=True)
class BaseCommand:
    issuer: EntityId
    sequence: int
    TYPE: ClassVar[str] = "NONE"

    @property
    @abstractmethod
    def sort_key(self) -> tuple:
        pass

    @abstractmethod
    def to_wire(self) -> dict[str, Any]:
        pass

    @classmethod
    @abstractmethod
    def from_wire(cls, data: dict[str, Any]) -> Self:
        pass


@dataclass(frozen=True, slots=True)
class MoveCommand(BaseCommand):
    targets: tuple[EntityId, ...]
    x: int
    TYPE: ClassVar[str] = "MOVE"

    @property
    def sort_key(self) -> tuple[int, int, str, tuple[int, ...], int]:
        return (
            int(self.issuer),
            self.sequence,
            self.TYPE,
            tuple(int(e) for e in self.targets),
            int(self.x),
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "type": self.TYPE,
            "issuer": int(self.issuer),
            "sequence": self.sequence,
            "targets": [int(e) for e in self.targets],
            "x": self.x,
        }

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> "MoveCommand":
        return cls(
            issuer=EntityId(int(data["issuer"])),
            sequence=int(data["sequence"]),
            targets=tuple(
                sorted([EntityId(int(e)) for e in data.get("targets", ())], key=int)
            ),
            x=max(-1, min(int(data["x"]), 1)),
        )


@dataclass(frozen=True, slots=True)
class JumpCommand(BaseCommand):
    targets: tuple[EntityId, ...]
    TYPE: ClassVar[str] = "JUMP"

    @property
    def sort_key(self) -> tuple[int, int, str, tuple[int, ...], int]:
        return (
            int(self.issuer),
            self.sequence,
            self.TYPE,
            tuple(int(e) for e in self.targets),
            0,
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "type": self.TYPE,
            "issuer": int(self.issuer),
            "sequence": self.sequence,
            "targets": [int(e) for e in self.targets],
        }

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> "JumpCommand":
        return cls(
            issuer=EntityId(int(data["issuer"])),
            sequence=int(data["sequence"]),
            targets=tuple(
                sorted([EntityId(int(e)) for e in data.get("targets", ())], key=int)
            ),
        )


@dataclass(frozen=True, slots=True)
class CommandFrame:
    tick: Tick
    commands: tuple[BaseCommand, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "commands",
            tuple(sorted(self.commands, key=lambda c: c.sort_key)),
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "kind": "command_frame",
            "tick": int(self.tick),
            "commands": [c.to_wire() for c in self.commands],
        }

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> "CommandFrame":
        wire_commands: list[BaseCommand] = []
        for payload in data.get("commands", ()):
            cmd_type = payload.get("type")
            if cmd_type == MoveCommand.TYPE:
                wire_commands.append(MoveCommand.from_wire(payload))
            elif cmd_type == JumpCommand.TYPE:
                wire_commands.append(JumpCommand.from_wire(payload))
            else:
                raise ValueError(f"Unknown command type: {cmd_type!r}")
        return cls(
            tick=Tick(int(data["tick"])),
            commands=tuple(wire_commands),
        )


def canonical_commands(commands: Iterable[BaseCommand]) -> tuple[BaseCommand, ...]:
    return tuple(sorted(commands, key=lambda c: c.sort_key))
