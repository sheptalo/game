from typing import TYPE_CHECKING

import esper

from game.collision import ObstacleBox, is_grounded, resolve_axis
from game.components.base import Collision, Movement, Position, RigidBody, Trigger

if TYPE_CHECKING:
    from config import InitialStateConfig


class MovementProcessor(esper.Processor):
    def __init__(self, config: InitialStateConfig) -> None:
        self._config = config
        super().__init__()

    def process(self) -> None:
        obstacles: list[ObstacleBox] = sorted(
            [
                (
                    eid,
                    pos.x - col.width // 2,
                    pos.x + col.width // 2,
                    pos.y - col.height // 2,
                    pos.y + col.height // 2,
                )
                for eid, (pos, col) in esper.get_components(Position, Collision)
                if not esper.has_component(eid, Trigger)
            ],
            key=lambda item: item[0],
        )
        pairs = sorted(
            esper.get_components(Position, Movement, Collision, RigidBody),
            key=lambda item: item[0],
        )
        for entity_id, (position, movement, collision, rigidbody) in pairs:
            col_w = collision.width
            col_h = collision.height

            if movement.x != 0:
                position.x = resolve_axis(
                    position.x,
                    position.y,
                    col_w,
                    col_h,
                    obstacles,
                    entity_id,
                    "x",
                    movement.x * self._config.move_step,
                )

            grounded = is_grounded(entity_id, position.x, position.y, col_w, col_h, obstacles)

            if movement.y == 1 and grounded:
                rigidbody.vy = self._config.jump_rise_speed
            movement.y = 0

            if rigidbody.vy > 0:
                old_y = position.y
                position.y = resolve_axis(position.x, position.y, col_w, col_h, obstacles, entity_id, "y", rigidbody.vy)
                if position.y == old_y:
                    rigidbody.vy = 0
                else:
                    rigidbody.vy = max(0, rigidbody.vy - self._config.jump_gravity)
            elif not grounded:
                rigidbody.vy = max(-self._config.fall_speed, rigidbody.vy - self._config.jump_gravity)
                position.y = resolve_axis(position.x, position.y, col_w, col_h, obstacles, entity_id, "y", rigidbody.vy)
            else:
                rigidbody.vy = 0
