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
    y: int
    TYPE: ClassVar[str] = "MOVE"

    @property
    def sort_key(self) -> tuple[int, int, str, tuple[int, ...], int]:
        return (
            int(self.issuer),
            self.sequence,
            self.TYPE,
            tuple(int(e) for e in self.targets),
            int(self.x) ^ int(self.y),
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "type": self.TYPE,
            "issuer": int(self.issuer),
            "sequence": self.sequence,
            "targets": [int(e) for e in self.targets],
            "x": self.x,
            "y": self.y,
        }

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> "MoveCommand":
        return cls(
            issuer=EntityId(int(data["issuer"])),
            sequence=int(data["sequence"]),
            targets=tuple(
                sorted([EntityId(int(e)) for e in data.get("targets", ())], key=int)
            ),
            x=int(data["x"]),
            y=int(data["y"]),
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
        return cls(
            tick=Tick(int(data["tick"])),
            commands=tuple(c.from_wire() for c in data.get("commands", ())),
        )


def canonical_commands(commands: Iterable[BaseCommand]) -> tuple[BaseCommand, ...]:
    return tuple(sorted(commands, key=lambda c: c.sort_key))
