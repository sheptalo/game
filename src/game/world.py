from dataclasses import fields
from typing import TYPE_CHECKING, Any

import esper

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

from config import InitialStateConfig
from core.types import EntityId
from game.components.base import Collision, Movement, OwnedBy, Position, RigidBody
from game.systems import SYSTEMS


def _spawn_platforms(config: InitialStateConfig) -> None:
    ground_y = config.spawn_start_y - config.unit_collision_height // 2 - 50
    esper.create_entity(
        Position(config.spawn_start_x, ground_y),
        Collision(8000, 100),
    )
    ceiling_y = config.spawn_start_y + 550
    esper.create_entity(
        Position(config.spawn_start_x + 2000, ceiling_y),
        Collision(800, 100),
    )
    esper.create_entity(
        Position(config.spawn_start_x, ceiling_y),
        Collision(800, 100),
    )


def init(config: InitialStateConfig) -> None:
    for system in SYSTEMS:
        esper.add_processor(system)
    _spawn_platforms(config)
    players = [
        esper.create_entity()
        for _ in range(config.player_count)
    ]
    for player_index, player in enumerate(players, start=1):
        column = (player_index - 1) % config.grid_columns
        row = (player_index - 1) // config.grid_columns
        x = config.spawn_start_x + column * config.spawn_step_x
        y = (
            config.spawn_start_y
            + row * config.spawn_step_y
            + config.spawn_air_offset
        )
        esper.create_entity(
            OwnedBy(EntityId(player)),
            Position(x, y),
            Movement(0, 0),
            Collision(config.unit_collision_width, config.unit_collision_height),
            RigidBody(0),
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
