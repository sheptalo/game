from __future__ import annotations

from ecs.coordinator import Coordinator
from ecs.system import System
from game.components import Movement, Position


class MovementSystem(System):
    def update(self, coordinator: Coordinator) -> None:
        for entity in self.sorted_entities():
            position = coordinator.get_component(entity, Position)
            movement = coordinator.get_component(entity, Movement)
            dx = movement.target_x - position.x
            dy = movement.target_y - position.y
            if dx == 0 and dy == 0:
                continue

            step = movement.speed
            if dx * dx + dy * dy <= step * step:
                position.x = movement.target_x
                position.y = movement.target_y
                continue

            dominant = max(abs(dx), abs(dy))
            position.x += _trunc_div(dx * step, dominant)
            position.y += _trunc_div(dy * step, dominant)


def _trunc_div(n: int, d: int) -> int:
    return -((-n) // d) if n < 0 else n // d
