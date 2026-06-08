from __future__ import annotations

MAX_COMPONENTS = 32


class Signature:
    __slots__ = ("value",)

    def __init__(self, value: int = 0) -> None:
        self.value = value

    def set(self, component_type: int) -> None:
        self.value |= 1 << component_type

    def unset(self, component_type: int) -> None:
        self.value &= ~(1 << component_type)

    def contains(self, required: Signature) -> bool:
        return (self.value & required.value) == required.value

    def copy(self) -> Signature:
        return Signature(self.value)
