from __future__ import annotations

from dataclasses import dataclass

from core.commands import Command, CommandType
from ecs.coordinator import Coordinator
from game.components import Movement, Owner


@dataclass(frozen=True, slots=True)
class CommandSystem:
    def apply(self, ecs: Coordinator, commands: tuple[Command, ...]) -> None:
        for command in commands:
            if command.type is not CommandType.MOVE or command.x is None or command.y is None:
                continue
            for unit_id in command.units:
                entity = int(unit_id)
                if not ecs.has_entity(entity):
                    continue
                if not ecs.has_component(entity, Owner) or not ecs.has_component(entity, Movement):
                    continue
                if ecs.get_component(entity, Owner).player_id != str(command.player_id):
                    continue
                movement = ecs.get_component(entity, Movement)
                movement.target_x = command.x
                movement.target_y = command.y
