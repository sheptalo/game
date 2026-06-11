import esper

from config import InitialStateConfig
from game.collision import is_grounded, resolve_fall_y, resolve_jump_y
from game.components.base import Collision, Movement, Position, RigidBody

_MOVE_CFG = InitialStateConfig()


class MovementProcessor(esper.Processor):
    def process(self) -> None:
        obstacles = sorted(
            (
                (entity_id, position, collision)
                for entity_id, (position, collision) in esper.get_components(
                    Position, Collision
                )
            ),
            key=lambda item: item[0],
        )
        pairs = sorted(
            esper.get_components(Position, Movement, Collision, RigidBody),
            key=lambda item: item[0],
        )
        for entity_id, (position, movement, collision, rigidbody) in pairs:
            if movement.x != 0:
                position.x += movement.x * _MOVE_CFG.move_step

            if movement.y == 1 and is_grounded(
                entity_id, position, collision, obstacles
            ):
                rigidbody.jump_remaining = _MOVE_CFG.jump_height
            movement.y = 0

            if rigidbody.jump_remaining > 0:
                rise = min(_MOVE_CFG.jump_rise_speed, rigidbody.jump_remaining)
                old_y = position.y
                position.y = resolve_jump_y(
                    position,
                    collision,
                    obstacles,
                    entity_id,
                    rise,
                )
                actual_rise = position.y - old_y

                if actual_rise == 0:
                    rigidbody.jump_remaining = 0
                    rigidbody.vy = _MOVE_CFG.fall_speed
                else:
                    rigidbody.jump_remaining -= actual_rise
                    rigidbody.vy = actual_rise
            elif not is_grounded(entity_id, position, collision, obstacles):
                position.y = resolve_fall_y(
                    position,
                    collision,
                    obstacles,
                    entity_id,
                    _MOVE_CFG.fall_speed,
                )
                rigidbody.vy = _MOVE_CFG.fall_speed
            else:
                rigidbody.vy = 0
