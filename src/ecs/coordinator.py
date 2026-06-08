from __future__ import annotations

from typing import TypeVar

from ecs.managers import ComponentManager, EntityManager, SystemManager
from ecs.system import System, TSystem
from ecs.types import ComponentType, Entity, Signature

T = TypeVar("T")


class Coordinator:
    """Single entry point; mediates entity, component, and system managers."""

    def __init__(self, max_entities: int | None = None) -> None:
        self._entities = (
            EntityManager() if max_entities is None else EntityManager(max_entities)
        )
        self._components = ComponentManager()
        self._systems = SystemManager()

    @property
    def next_entity_id(self) -> Entity:
        return self._entities.next_id

    @next_entity_id.setter
    def next_entity_id(self, value: Entity) -> None:
        self._entities.next_id = value

    def register_component(self, component_type: type) -> None:
        self._components.register(component_type)

    def register_system(self, system_type: type[TSystem]) -> TSystem:
        return self._systems.register(system_type)

    def set_system_signature(self, system_type: type[System], signature: Signature) -> None:
        self._systems.set_signature(system_type, signature)
        for entity in self._entities.living_sorted():
            self._systems.entity_signature_changed(entity, self._entities.signature(entity))

    def create_entity(self) -> Entity:
        return self._entities.create()

    def register_entity(self, entity: Entity) -> Entity:
        return self._entities.register(entity)

    def destroy_entity(self, entity: Entity) -> None:
        self._entities.destroy(entity)
        self._components.entity_destroyed(entity)
        self._systems.entity_destroyed(entity)

    def add_component(self, entity: Entity, component: object) -> None:
        self._components.add(entity, component)
        self._entities.signature(entity).set(self._components.type_id(type(component)))
        self._systems.entity_signature_changed(entity, self._entities.signature(entity))

    def remove_component(self, entity: Entity, component_type: type) -> None:
        self._components.remove(entity, component_type)
        self._entities.signature(entity).unset(self._components.type_id(component_type))
        self._systems.entity_signature_changed(entity, self._entities.signature(entity))

    def get_component(self, entity: Entity, component_type: type[T]) -> T:
        return self._components.get(entity, component_type)

    def has_component(self, entity: Entity, component_type: type) -> bool:
        return self._components.has(entity, component_type)

    def component_type_id(self, component_type: type) -> ComponentType:
        return self._components.type_id(component_type)

    def entity_signature(self, entity: Entity) -> Signature:
        return self._entities.signature(entity)

    def has_entity(self, entity: Entity) -> bool:
        return self._entities.has(entity)

    def living_entities_sorted(self) -> list[Entity]:
        return self._entities.living_sorted()

    def make_signature(self, *component_types: type) -> Signature:
        signature = Signature()
        for component_type in component_types:
            signature.set(self._components.type_id(component_type))
        return signature

    def get_system(self, system_type: type[TSystem]) -> TSystem:
        return self._systems.get(system_type)
