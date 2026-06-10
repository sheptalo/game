from __future__ import annotations

from typing import Any

import esper

from config import InitialStateConfig
from core.types import EntityId
from game.components.base import Movement, OwnedBy, Position, Resources
from game.registry import entity_to_record
from game.systems import SYSTEMS


def init(config: InitialStateConfig) -> None:
    esper.clear_database()
    for system in SYSTEMS:
        esper.add_processor(system)

    for _ in range(config.player_count):
        player = create(Resources(config.player_resources))
        column = (player - 1) % config.grid_columns
        row = (player - 1) // config.grid_columns
        x = config.spawn_start_x + column * config.spawn_step_x
        y = config.spawn_start_y + row * config.spawn_step_y
        create(
            OwnedBy(EntityId(player)),
            Position(x, y),
            Movement(x, y, config.unit_speed),
        )


def create(*components: object) -> int:
    entity = esper.create_entity()
    for component in components:
        esper.add_component(entity, component)
    return entity


def snapshot() -> dict[str, Any]:
    return {
        "next_entity_id": esper._entity_count,
        "entities": [
            entity_to_record(entity_id)
            for entity_id in sorted(entity for entity in esper.get_entities())
        ],
    }
