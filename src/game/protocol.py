from __future__ import annotations

from typing import Any

from core.commands import Command, CommandType
from core.types import EntityId


def player_slot_to_entity(slot: str) -> EntityId:
    if slot.startswith("p"):
        return EntityId(int(slot[1:]))
    return EntityId(int(slot))


def entity_to_player_slot(entity_id: EntityId | int) -> str:
    return f"p{int(entity_id)}"


def command_from_client_wire(data: dict[str, Any]) -> Command:
    if "issuer" in data:
        issuer = EntityId(int(data["issuer"]))
        targets = tuple(EntityId(int(entity_id)) for entity_id in data.get("targets", ()))
    else:
        issuer = player_slot_to_entity(str(data["player_id"]))
        targets = tuple(
            EntityId(int(entity_id)) for entity_id in data.get("units", data.get("targets", ()))
        )

    return Command(
        type=CommandType(data["type"]),
        issuer=issuer,
        sequence=int(data["sequence"]),
        targets=targets,
        x=int(data["x"]) if "x" in data else None,
        y=int(data["y"]) if "y" in data else None,
    )


def command_to_client_wire(command: Command) -> dict[str, Any]:
    wire = command.to_wire()
    wire["player_id"] = entity_to_player_slot(command.issuer)
    if command.targets:
        wire["units"] = wire.pop("targets")
    return wire
