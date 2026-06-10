from typing import Any

from core.commands import Command, CommandType
from core.types import EntityId


def command_from_client_wire(data: dict[str, Any]) -> Command:
    if "issuer" in data:
        issuer = EntityId(int(data["issuer"]))
        targets = tuple(
            EntityId(int(entity_id)) for entity_id in data.get("targets", ())
        )
    else:
        player_id = str(data["player_id"])
        issuer = EntityId(int(player_id))
        targets = tuple(
            EntityId(int(entity_id))
            for entity_id in data.get("units", data.get("targets", ()))
        )

    return Command(
        type=CommandType(data["type"]),
        issuer=issuer,
        sequence=int(data["sequence"]),
        targets=targets,
        x=int(data["x"]) if "x" in data else None,
        y=int(data["y"]) if "y" in data else None,
    )
