import esper

from game.components import Position


def teleport_to_0(unit_id):
    position = esper.component_for_entity(unit_id, Position)
    position.x = 0
    position.y = 0


def teleport_to_5000(unit_id):
    position = esper.component_for_entity(unit_id, Position)
    position.x = 5000
    position.y = 5000
