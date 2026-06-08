from __future__ import annotations

from typing import Any

from config import InitialStateConfig
from core.types import EntityId
from game.components import Movement, OwnedBy, Position, Resources
from game.world import World


def build_initial_state(config: InitialStateConfig) -> dict[str, Any]:
    world = World()

    for player_number in range(1, config.player_count + 1):
        world.create(player_number, Resources(config.player_resources))

    for player_number in range(1, config.player_count + 1):
        column = (player_number - 1) % config.grid_columns
        row = (player_number - 1) // config.grid_columns
        x = config.spawn_start_x + column * config.spawn_step_x
        y = config.spawn_start_y + row * config.spawn_step_y
        world.create(
            config.player_count + player_number,
            OwnedBy(EntityId(player_number)),
            Position(x, y),
            Movement(x, y, config.unit_speed),
        )

    return world.to_snapshot()
