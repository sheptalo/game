from __future__ import annotations

from typing import NewType

Tick = NewType("Tick", int)
EntityId = NewType("EntityId", int)

FIXED_POINT_SCALE = 1000


def fixed(value: float | int) -> int:
    return int(round(float(value) * FIXED_POINT_SCALE))


def unfixed(value: int) -> float:
    return value / FIXED_POINT_SCALE
