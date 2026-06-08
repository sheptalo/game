from __future__ import annotations

from ecs.component_array import ComponentArray


class ComponentManager:
    __slots__ = ("_arrays", "_component_types", "_next_component_type")

    def __init__(self) -> None:
        self._component_types: dict[type, int] = {}
        self._arrays: dict[type, ComponentArray] = {}
        self._next_component_type = 0

    def register_component[T](self, component_type: type[T]) -> None:
        if component_type in self._component_types:
            raise ValueError(f"component {component_type.__name__} already registered")

        type_id = self._next_component_type
        self._next_component_type += 1
        self._component_types[component_type] = type_id
        self._arrays[component_type] = ComponentArray()

    def get_component_type(self, component_type: type) -> int:
        if component_type not in self._component_types:
            raise ValueError(f"component {component_type.__name__} is not registered")
        return self._component_types[component_type]

    def add_component[T](self, entity: int, component: T) -> None:
        component_type = type(component)
        self._arrays[component_type].insert(entity, component)

    def remove_component[T](self, entity: int, component_type: type[T]) -> None:
        self._arrays[component_type].remove(entity)

    def get_component[T](self, entity: int, component_type: type[T]) -> T:
        return self._arrays[component_type].get(entity)

    def has_component(self, entity: int, component_type: type) -> bool:
        return self._arrays[component_type].has(entity)

    def entity_destroyed(self, entity: int) -> None:
        for array in self._arrays.values():
            array.entity_destroyed(entity)
