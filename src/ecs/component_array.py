from __future__ import annotations


class ComponentArray[T]:
    """Packed component storage with entity-to-index mapping and swap-and-pop removal."""

    __slots__ = (
        "_components",
        "_entity_to_index",
        "_index_to_entity",
        "_size",
    )

    def __init__(self) -> None:
        self._components: list[T] = []
        self._entity_to_index: dict[int, int] = {}
        self._index_to_entity: dict[int, int] = {}
        self._size = 0

    def insert(self, entity: int, component: T) -> None:
        if entity in self._entity_to_index:
            raise ValueError(f"component already exists for entity {entity}")

        index = self._size
        self._entity_to_index[entity] = index
        self._index_to_entity[index] = entity
        self._components.append(component)
        self._size += 1

    def remove(self, entity: int) -> None:
        if entity not in self._entity_to_index:
            raise ValueError(f"component missing for entity {entity}")

        index = self._entity_to_index[entity]
        last_index = self._size - 1

        if index != last_index:
            last_entity = self._index_to_entity[last_index]
            self._components[index] = self._components[last_index]
            self._entity_to_index[last_entity] = index
            self._index_to_entity[index] = last_entity

        self._components.pop()
        del self._entity_to_index[entity]
        del self._index_to_entity[last_index]
        self._size -= 1

    def get(self, entity: int) -> T:
        return self._components[self._entity_to_index[entity]]

    def has(self, entity: int) -> bool:
        return entity in self._entity_to_index

    def entity_destroyed(self, entity: int) -> None:
        if self.has(entity):
            self.remove(entity)
