import esper

from game.components import Position


def teleport(unit_id):
    position = esper.component_for_entity(unit_id, Position)
    position.x = 0
    position.y = 0


def spawn(unit_id):
    position = esper.component_for_entity(unit_id, Position)
    position.x = 4000
    position.y = 4000
