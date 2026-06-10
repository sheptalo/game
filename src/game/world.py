from __future__ import annotations

from typing import Any

import esper

from config import InitialStateConfig
from core.types import EntityId
from game.components.base import Movement, OwnedBy, Position, Resources
from game.registry import entity_to_record
from game.systems.movement import MovementProcessor

_next_entity_id = 1


def init(config: InitialStateConfig) -> None:
    global _next_entity_id
    esper.clear_database()
    _next_entity_id = 1
    if esper.get_processor(MovementProcessor) is None:
        esper.add_processor(MovementProcessor())

    for player_number in range(1, config.player_count + 1):
        create(player_number, Resources(config.player_resources))

    for player_number in range(1, config.player_count + 1):
        column = (player_number - 1) % config.grid_columns
        row = (player_number - 1) // config.grid_columns
        x = config.spawn_start_x + column * config.spawn_step_x
        y = config.spawn_start_y + row * config.spawn_step_y
        create(
            config.player_count + player_number,
            OwnedBy(EntityId(player_number)),
            Position(x, y),
            Movement(x, y, config.unit_speed),
        )


def create(entity_id: int, *components: object) -> int:
    global _next_entity_id
    while _next_entity_id < entity_id:
        placeholder = esper.create_entity()
        esper.delete_entity(placeholder, immediate=True)
        _next_entity_id += 1

    entity = esper.create_entity()
    if entity != entity_id:
        raise ValueError(f"expected entity {entity_id}, got {entity}")
    _next_entity_id = entity_id + 1

    for component in components:
        esper.add_component(entity, component)
    return entity


def entity_ids() -> list[int]:
    return sorted(
        entity for entity in esper.get_entities() if esper.entity_exists(entity)
    )


def snapshot() -> dict[str, Any]:
    return {
        "next_entity_id": _next_entity_id,
        "entities": [entity_to_record(entity_id) for entity_id in entity_ids()],
    }
