from __future__ import annotations

from ecs.signature import Signature
from ecs.system import System


class SystemManager:
    __slots__ = ("_signatures", "_systems")

    def __init__(self) -> None:
        self._systems: dict[type[System], System] = {}
        self._signatures: dict[type[System], Signature] = {}

    def register_system[T: System](self, system_type: type[T]) -> T:
        if system_type in self._systems:
            raise ValueError(f"system {system_type.__name__} already registered")

        system = system_type()
        self._systems[system_type] = system
        return system

    def get_system[T: System](self, system_type: type[T]) -> T:
        return self._systems[system_type]

    def set_signature(self, system_type: type[System], signature: Signature) -> None:
        if system_type not in self._systems:
            raise ValueError(f"system {system_type.__name__} is not registered")

        self._signatures[system_type] = signature.copy()
        system = self._systems[system_type]
        system.entities.clear()

    def entity_destroyed(self, entity: int) -> None:
        for system in self._systems.values():
            system.entities.discard(entity)

    def entity_signature_changed(
        self, entity: int, entity_signature: Signature
    ) -> None:
        for system_type, system in self._systems.items():
            required = self._signatures.get(system_type)
            if required is None:
                continue
            if entity_signature.contains(required):
                system.entities.add(entity)
            else:
                system.entities.discard(entity)

    def rebuild_entity(self, entity: int, entity_signature: Signature) -> None:
        self.entity_signature_changed(entity, entity_signature)
