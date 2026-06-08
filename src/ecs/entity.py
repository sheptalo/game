from __future__ import annotations

from collections import deque

from ecs.signature import Signature

MAX_ENTITIES = 65536


class EntityManager:
    """Entity id pool, living set, and per-entity component signatures."""

    __slots__ = (
        "_available",
        "_living",
        "_max_entities",
        "_next_id",
        "_signatures",
    )

    def __init__(self, max_entities: int = MAX_ENTITIES) -> None:
        self._max_entities = max_entities
        self._available: deque[int] = deque()
        self._living: set[int] = set()
        self._next_id = 1
        self._signatures = [Signature() for _ in range(max_entities)]

    @property
    def next_id(self) -> int:
        return self._next_id

    @next_id.setter
    def next_id(self, value: int) -> None:
        self._next_id = value

    def create_entity(self) -> int:
        if self._available:
            entity = self._available.popleft()
        else:
            entity = self._next_id
            self._next_id += 1

        if entity >= self._max_entities:
            raise ValueError(
                f"entity id {entity} exceeds MAX_ENTITIES ({self._max_entities})"
            )

        self._living.add(entity)
        return entity

    def register_entity(self, entity: int) -> int:
        if entity in self._living:
            raise ValueError(f"duplicate entity id {entity}")
        if entity >= self._max_entities:
            raise ValueError(
                f"entity id {entity} exceeds MAX_ENTITIES ({self._max_entities})"
            )

        if entity in self._available:
            self._available = deque(item for item in self._available if item != entity)

        if entity >= self._next_id:
            self._next_id = entity + 1

        self._living.add(entity)
        return entity

    def destroy_entity(self, entity: int) -> None:
        if entity not in self._living:
            raise ValueError(f"entity {entity} does not exist")

        self._signatures[entity] = Signature()
        self._living.remove(entity)
        self._available.append(entity)

    def has(self, entity: int) -> bool:
        return entity in self._living

    def living_entities_sorted(self) -> list[int]:
        return sorted(self._living)

    def get_signature(self, entity: int) -> Signature:
        return self._signatures[entity]

    def set_signature(self, entity: int, signature: Signature) -> None:
        self._signatures[entity] = signature.copy()
