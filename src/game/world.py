from dataclasses import fields
from typing import TYPE_CHECKING, Any

import esper

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

from config import InitialStateConfig
from core.types import EntityId
from game.components.base import Movement, OwnedBy, Position, Resources
from game.systems import SYSTEMS


def init(config: InitialStateConfig) -> None:
    for system in SYSTEMS:
        esper.add_processor(system)

    # Create all player entities first so they get sequential ids 1..N;
    # the spawn grid below and external clients rely on that numbering.
    players = [
        esper.create_entity(Resources(config.player_resources))
        for _ in range(config.player_count)
    ]
    for player in players:
        column = (player - 1) % config.grid_columns
        row = (player - 1) // config.grid_columns
        x = config.spawn_start_x + column * config.spawn_step_x
        y = config.spawn_start_y + row * config.spawn_step_y
        esper.create_entity(
            OwnedBy(EntityId(player)),
            Position(x, y),
            Movement(x, y, config.unit_speed),
        )


def snapshot() -> dict[str, Any]:
    return {
        "next_entity_id": max(esper.get_entities(), default=0) + 1,
        "entities": [
            entity_to_record(entity_id)
            for entity_id in sorted(entity for entity in esper.get_entities())
        ],
    }


def entity_to_record(entity_id: int) -> dict[str, Any]:
    record: dict[str, Any] = {"id": entity_id}
    component: DataclassInstance
    for component in esper.components_for_entity(entity_id):
        payload = {f.name: getattr(component, f.name) for f in fields(component)}
        record[component.__class__.__name__] = payload
    return record
