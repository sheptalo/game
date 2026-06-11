import esper

from game.components.base import Movement, Position


class MovementProcessor(esper.Processor):
    def process(self) -> None:
        pairs = sorted(
            esper.get_components(Position, Movement), key=lambda item: item[0]
        )
        for _entity, (position, movement) in pairs:
            if movement.x == 0 and movement.y == 0:
                continue

            step = 50
            jump_height = 1000
            position.x += movement.x * step
            position.y += movement.y * jump_height
