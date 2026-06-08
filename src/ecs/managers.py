from __future__ import annotations

from collections import deque
from typing import TypeVar, cast

from ecs.component_array import ComponentArray
from ecs.system import System, TSystem
from ecs.types import MAX_ENTITIES, ComponentType, Entity, Signature

T = TypeVar("T")


class EntityManager:
    def __init__(self, max_entities: int = MAX_ENTITIES) -> None:
        self._max_entities = max_entities
        self._available: deque[Entity] = deque()
        self._living: set[Entity] = set()
        self._next_id: Entity = 1
        self._signatures = [Signature() for _ in range(max_entities)]

    @property
    def next_id(self) -> Entity:
        return self._next_id

    @next_id.setter
    def next_id(self, value: Entity) -> None:
        self._next_id = value

    def create(self) -> Entity:
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

    def register(self, entity: Entity) -> Entity:
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

    def destroy(self, entity: Entity) -> None:
        if entity not in self._living:
            raise ValueError(f"entity {entity} does not exist")
        self._signatures[entity] = Signature()
        self._living.remove(entity)
        self._available.append(entity)

    def has(self, entity: Entity) -> bool:
        return entity in self._living

    def living_sorted(self) -> list[Entity]:
        return sorted(self._living)

    def signature(self, entity: Entity) -> Signature:
        return self._signatures[entity]


class ComponentManager:
    def __init__(self) -> None:
        self._types: dict[type, ComponentType] = {}
        self._arrays: dict[type, ComponentArray] = {}
        self._next_type: ComponentType = 0

    def register(self, component_type: type[T]) -> None:
        if component_type in self._types:
            raise ValueError(f"component {component_type.__name__} already registered")
        self._types[component_type] = self._next_type
        self._arrays[component_type] = ComponentArray()
        self._next_type += 1

    def type_id(self, component_type: type) -> ComponentType:
        if component_type not in self._types:
            raise ValueError(f"component {component_type.__name__} is not registered")
        return self._types[component_type]

    def add(self, entity: Entity, component: T) -> None:
        self._arrays[type(component)].insert(entity, component)

    def remove(self, entity: Entity, component_type: type[T]) -> None:
        self._arrays[component_type].remove(entity)

    def get(self, entity: Entity, component_type: type[T]) -> T:
        return self._arrays[component_type].get(entity)

    def has(self, entity: Entity, component_type: type) -> bool:
        return self._arrays[component_type].has(entity)

    def entity_destroyed(self, entity: Entity) -> None:
        for array in self._arrays.values():
            array.entity_destroyed(entity)


class SystemManager:
    def __init__(self) -> None:
        self._systems: dict[type[System], System] = {}
        self._signatures: dict[type[System], Signature] = {}

    def register(self, system_type: type[TSystem]) -> TSystem:
        if system_type in self._systems:
            raise ValueError(f"system {system_type.__name__} already registered")
        system = system_type()
        self._systems[system_type] = system
        return system

    def get(self, system_type: type[TSystem]) -> TSystem:
        return cast(TSystem, self._systems[system_type])

    def set_signature(self, system_type: type[System], signature: Signature) -> None:
        if system_type not in self._systems:
            raise ValueError(f"system {system_type.__name__} is not registered")
        self._signatures[system_type] = Signature(signature.value)
        self._systems[system_type].entities.clear()

    def entity_destroyed(self, entity: Entity) -> None:
        for system in self._systems.values():
            system.entities.discard(entity)

    def entity_signature_changed(
        self, entity: Entity, entity_signature: Signature
    ) -> None:
        for system_type, system in self._systems.items():
            required = self._signatures.get(system_type)
            if required is None:
                continue
            if entity_signature.contains(required):
                system.entities.add(entity)
            else:
                system.entities.discard(entity)
