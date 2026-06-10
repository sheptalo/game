from dataclasses import dataclass

from core.types import EntityId


@dataclass(slots=True)
class Resources:
    amount: int


@dataclass(slots=True)
class Position:
    x: int
    y: int


@dataclass(slots=True)
class Movement:
    target_x: int
    target_y: int
    speed: int


@dataclass(slots=True)
class OwnedBy:
    owner: EntityId
