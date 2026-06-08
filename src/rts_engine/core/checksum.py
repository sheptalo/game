from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Checksum:
    tick: int
    value: str

    def to_wire(self) -> dict[str, int | str]:
        return {"kind": "checksum", "tick": self.tick, "value": self.value}


class ChecksumBuilder:
    """Browser-compatible FNV-1a checksum builder for deterministic state validation."""

    def __init__(self) -> None:
        self._hash = 2166136261

    def add_int(self, value: int) -> None:
        self._add_text(f"i:{int(value)};")

    def add_str(self, value: str) -> None:
        text = str(value)
        self._add_text(f"s:{len(text)}:{text};")

    def digest(self) -> str:
        return f"{self._hash:08x}"

    def _add_text(self, text: str) -> None:
        for char in text:
            self._hash ^= ord(char)
            self._hash = (self._hash * 16777619) & 0xFFFFFFFF
