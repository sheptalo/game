import esper

from core.commands import Command, CommandType
from game.components.base import Movement, OwnedBy


def apply_commands(commands: tuple[Command, ...]) -> None:
    for command in commands:
        if (
            command.type is not CommandType.MOVE
            or command.x is None
            or command.y is None
        ):
            continue
        for target in command.targets:
            entity = int(target)
            if not esper.entity_exists(entity):
                continue
            if not esper.has_components(entity, OwnedBy, Movement):
                continue
            if int(esper.component_for_entity(entity, OwnedBy).owner) != int(
                command.issuer
            ):
                continue
            movement = esper.component_for_entity(entity, Movement)
            movement.target_x = command.x
            movement.target_y = command.y


def step(commands: tuple[Command, ...]) -> None:
    apply_commands(commands)
    esper.process()
