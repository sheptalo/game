import esper

from game.components.base import Movement, Position


class MovementProcessor(esper.Processor):
    def process(self) -> None:
        for _entity, (position, movement) in esper.get_components(Position, Movement):
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
