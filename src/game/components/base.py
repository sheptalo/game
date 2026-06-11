from dataclasses import dataclass, field

from core.types import EntityId


@dataclass(slots=True)
class Position:
    x: int
    y: int


@dataclass(slots=True)
class Movement:
    x: int
    y: int


@dataclass(slots=True)
class Collision:
    width: int
    height: int


@dataclass(slots=True)
class Trigger:
    on_enter: str
    on_exit: str


@dataclass(slots=True)
class TriggerOverlap:
    inside: list[int] = field(default_factory=list)


@dataclass(slots=True)
class RigidBody:
    vy: int = 0
    jump_remaining: int = 0


@dataclass(slots=True)
class OwnedBy:
    owner: EntityId
