import esper

from core.commands import Command, CommandType
from game.components import Movement, OwnedBy


def _apply_commands(commands: tuple[Command, ...]) -> None:
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
            owned, movement = esper.try_components(entity, OwnedBy, Movement)
            if not owned or not movement or int(owned.owner) != int(command.issuer):
                continue
            movement.target_x = command.x
            movement.target_y = command.y


def step(commands: tuple[Command, ...]) -> None:
    _apply_commands(commands)
    esper.process()
