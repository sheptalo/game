from __future__ import annotations

from dataclasses import dataclass


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
class Health:
    hp: int


@dataclass(slots=True)
class Owner:
    player_id: str
