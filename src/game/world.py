from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import count
from typing import Any, Generator

import esper

from game.registry import apply_record, entity_to_record
from game.systems.movement import MovementProcessor

_context_counter = count(1)


@dataclass(slots=True)
class World:
    context: str = field(default_factory=lambda: f"world-{next(_context_counter)}")
    next_entity_id: int = 1

    def __post_init__(self) -> None:
        with self.bind():
            esper.clear_database()
            if esper.get_processor(MovementProcessor) is None:
                esper.add_processor(MovementProcessor())

    @contextmanager
    def bind(self) -> Generator[None]:
        esper.switch_world(self.context)
        yield

    def create(self, entity_id: int, *components: object) -> int:
        with self.bind():
            entity = self._allocate(entity_id)
            for component in components:
                esper.add_component(entity, component)
            return entity

    def delete(self, entity_id: int) -> None:
        with self.bind():
            if esper.entity_exists(entity_id):
                esper.delete_entity(entity_id, immediate=True)

    def entity_ids(self) -> list[int]:
        with self.bind():
            return sorted(
                entity for entity in esper.get_entities() if esper.entity_exists(entity)
            )

    def to_snapshot(self) -> dict[str, Any]:
        with self.bind():
            return {
                "next_entity_id": self.next_entity_id,
                "entities": [
                    entity_to_record(entity_id) for entity_id in self.entity_ids()
                ],
            }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> World:
        world = cls()
        with world.bind():
            world.next_entity_id = 1
            for record in snapshot["entities"]:
                apply_record(world, record)
            world.next_entity_id = int(snapshot["next_entity_id"])
        return world

    def _allocate(self, entity_id: int) -> int:
        while self.next_entity_id < entity_id:
            placeholder = esper.create_entity()
            esper.delete_entity(placeholder, immediate=True)
            self.next_entity_id += 1

        entity = esper.create_entity()
        if entity != entity_id:
            raise ValueError(f"expected entity {entity_id}, got {entity}")
        self.next_entity_id = entity_id + 1
        return entity
