from typing import Any

import msgpack


class ProtocolError(ValueError):
    pass


def pack_message(message: dict[str, Any]) -> bytes:
    return msgpack.packb(message, use_bin_type=True, strict_types=True)


def unpack_message(payload: bytes) -> dict[str, Any]:
    message = msgpack.unpackb(payload, raw=False, strict_map_key=False)
    if not isinstance(message, dict):
        raise ProtocolError("wire message must be a map")
    return message
