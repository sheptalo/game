from __future__ import annotations

from ecs.types import Entity


class ComponentArray[T]:
    """Packed array; entity id maps to dense index (swap-and-pop on remove)."""

    __slots__ = ("_components", "_entity_to_index", "_index_to_entity")

    def __init__(self) -> None:
        self._components: list[T] = []
        self._entity_to_index: dict[Entity, int] = {}
        self._index_to_entity: dict[int, Entity] = {}

    def insert(self, entity: Entity, component: T) -> None:
        if entity in self._entity_to_index:
            raise ValueError(f"component already exists for entity {entity}")
        index = len(self._components)
        self._entity_to_index[entity] = index
        self._index_to_entity[index] = entity
        self._components.append(component)

    def remove(self, entity: Entity) -> None:
        if entity not in self._entity_to_index:
            raise ValueError(f"component missing for entity {entity}")
        index = self._entity_to_index[entity]
        last = len(self._components) - 1
        if index != last:
            moved_entity = self._index_to_entity[last]
            self._components[index] = self._components[last]
            self._entity_to_index[moved_entity] = index
            self._index_to_entity[index] = moved_entity
        self._components.pop()
        del self._entity_to_index[entity]
        del self._index_to_entity[last]

    def get(self, entity: Entity) -> T:
        return self._components[self._entity_to_index[entity]]

    def has(self, entity: Entity) -> bool:
        return entity in self._entity_to_index

    def entity_destroyed(self, entity: Entity) -> None:
        if self.has(entity):
            self.remove(entity)
