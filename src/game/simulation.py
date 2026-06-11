import esper

from core.commands import BaseCommand, MoveCommand
from game.components import Movement, OwnedBy


def _apply_commands(commands: tuple[BaseCommand, ...]) -> None:
    for command in commands:
        if not isinstance(command, MoveCommand):
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


def step(commands: tuple[BaseCommand, ...]) -> None:
    _apply_commands(commands)
    esper.process()
