from __future__ import annotations

from typing import Any


class ChecksumBuilder:
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


def _write_value(builder: ChecksumBuilder, value: Any) -> None:
    if isinstance(value, bool):
        builder.add_str("bool")
        builder.add_int(int(value))
    elif isinstance(value, int):
        builder.add_str("int")
        builder.add_int(value)
    else:
        builder.add_str("str")
        builder.add_str(str(value))


def _write_component(
    builder: ChecksumBuilder, name: str, payload: dict[str, Any]
) -> None:
    builder.add_str(name)
    for field in sorted(payload):
        builder.add_str(field)
        _write_value(builder, payload[field])


def checksum_snapshot(tick: int, snapshot: dict[str, Any]) -> str:
    builder = ChecksumBuilder()
    builder.add_int(tick)
    builder.add_int(int(snapshot["next_entity_id"]))
    for entity in sorted(snapshot["entities"], key=lambda record: int(record["id"])):
        builder.add_int(int(entity["id"]))
        for component_name in sorted(key for key in entity if key != "id"):
            _write_component(builder, component_name, entity[component_name])
    return builder.digest()
