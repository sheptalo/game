from dataclasses import dataclass

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
class OwnedBy:
    owner: EntityId
