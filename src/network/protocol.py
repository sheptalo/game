from __future__ import annotations

from typing import Any

import msgpack

from core.commands import CommandFrame


class ProtocolError(ValueError):
    pass


def pack_message(message: dict[str, Any]) -> bytes:
    return msgpack.packb(message, use_bin_type=True, strict_types=True)


def unpack_message(payload: bytes) -> dict[str, Any]:
    message = msgpack.unpackb(payload, raw=False, strict_map_key=False)
    if not isinstance(message, dict):
        raise ProtocolError("wire message must be a map")
    return message


def encode_command_frame(frame: CommandFrame) -> bytes:
    return pack_message(frame.to_wire())


def decode_command_frame(payload: bytes) -> CommandFrame:
    message = unpack_message(payload)
    if message.get("kind") != "command_frame":
        raise ProtocolError(f"expected command_frame, got {message.get('kind')!r}")
    return CommandFrame.from_wire(message)
