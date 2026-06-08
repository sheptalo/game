from __future__ import annotations

Entity = int
ComponentType = int

MAX_ENTITIES = 65536
MAX_COMPONENTS = 32


class Signature:
    __slots__ = ("value",)

    def __init__(self, value: int = 0) -> None:
        self.value = value

    def set(self, component_type: ComponentType) -> None:
        self.value |= 1 << component_type

    def unset(self, component_type: ComponentType) -> None:
        self.value &= ~(1 << component_type)

    def contains(self, required: Signature) -> bool:
        return (self.value & required.value) == required.value
