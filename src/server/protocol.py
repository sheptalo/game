import msgpack


def pack_message(message: dict) -> bytes:
    return msgpack.packb(message, use_bin_type=True, strict_types=True)


def unpack_message(payload: bytes) -> dict:
    message = msgpack.unpackb(payload, raw=False, strict_map_key=False)
    if not isinstance(message, dict):
        raise ValueError("wire message must be a map")
    return message
