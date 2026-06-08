from __future__ import annotations

from ecs.component_manager import ComponentManager
from ecs.entity import EntityManager
from ecs.signature import Signature
from ecs.system import System
from ecs.system_manager import SystemManager


class Coordinator:
    __slots__ = (
        "_component_manager",
        "_entity_manager",
        "_system_manager",
    )

    def __init__(self, max_entities: int | None = None) -> None:
        self._entity_manager = (
            EntityManager() if max_entities is None else EntityManager(max_entities)
        )
        self._component_manager = ComponentManager()
        self._system_manager = SystemManager()

    @property
    def entity_manager(self) -> EntityManager:
        return self._entity_manager

    @property
    def component_manager(self) -> ComponentManager:
        return self._component_manager

    @property
    def system_manager(self) -> SystemManager:
        return self._system_manager

    def register_component[T](self, component_type: type[T]) -> None:
        self._component_manager.register_component(component_type)

    def register_system[T: System](self, system_type: type[T]) -> T:
        return self._system_manager.register_system(system_type)

    def set_system_signature(
        self, system_type: type[System], signature: Signature
    ) -> None:
        self._system_manager.set_signature(system_type, signature)
        for entity in self._entity_manager.living_entities_sorted():
            self._system_manager.rebuild_entity(
                entity,
                self._entity_manager.get_signature(entity),
            )

    def create_entity(self) -> int:
        return self._entity_manager.create_entity()

    def register_entity(self, entity: int) -> int:
        return self._entity_manager.register_entity(entity)

    def destroy_entity(self, entity: int) -> None:
        self._entity_manager.destroy_entity(entity)
        self._component_manager.entity_destroyed(entity)
        self._system_manager.entity_destroyed(entity)

    def add_component[T](self, entity: int, component: T) -> None:
        self._component_manager.add_component(entity, component)
        component_type = self._component_manager.get_component_type(type(component))
        signature = self._entity_manager.get_signature(entity)
        signature.set(component_type)
        self._entity_manager.set_signature(entity, signature)
        self._system_manager.entity_signature_changed(entity, signature)

    def remove_component[T](self, entity: int, component_type: type[T]) -> None:
        self._component_manager.remove_component(entity, component_type)
        type_id = self._component_manager.get_component_type(component_type)
        signature = self._entity_manager.get_signature(entity)
        signature.unset(type_id)
        self._entity_manager.set_signature(entity, signature)
        self._system_manager.entity_signature_changed(entity, signature)

    def get_component[T](self, entity: int, component_type: type[T]) -> T:
        return self._component_manager.get_component(entity, component_type)

    def has_component(self, entity: int, component_type: type) -> bool:
        return self._component_manager.has_component(entity, component_type)

    def has_entity(self, entity: int) -> bool:
        return self._entity_manager.has(entity)

    def living_entities_sorted(self) -> list[int]:
        return self._entity_manager.living_entities_sorted()

    def make_signature(self, *component_types: type) -> Signature:
        signature = Signature()
        for component_type in component_types:
            signature.set(self._component_manager.get_component_type(component_type))
        return signature

    def get_system[T: System](self, system_type: type[T]) -> T:
        return self._system_manager.get_system(system_type)
