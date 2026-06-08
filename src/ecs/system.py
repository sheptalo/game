from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ecs.coordinator import Coordinator


class System:
    __slots__ = ("entities",)

    def __init__(self) -> None:
        self.entities: set[int] = set()

    def sorted_entities(self) -> list[int]:
        return sorted(self.entities)

    def update(self, coordinator: Coordinator) -> None:
        raise NotImplementedError
