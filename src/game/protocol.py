from typing import Any

from core.commands import BaseCommand, MoveCommand


def command_from_client_wire(data: dict[str, Any]) -> BaseCommand:
    cmd_type = data.get("type")
    if cmd_type == MoveCommand.TYPE:
        return MoveCommand.from_wire(data)
    raise ValueError(f"Unknown command type: {cmd_type!r}")
