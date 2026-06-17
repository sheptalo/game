from typing import Any

from core.commands import BaseCommand, JumpCommand, MoveCommand


def command_from_client_wire(data: dict[str, Any], issuer: Any) -> BaseCommand:
    data = {**data, "issuer": int(issuer)}
    cmd_type = data.get("type")
    if cmd_type == MoveCommand.TYPE:
        return MoveCommand.from_wire(data)
    if cmd_type == JumpCommand.TYPE:
        return JumpCommand.from_wire(data)
    raise ValueError(f"Unknown command type: {cmd_type!r}")
