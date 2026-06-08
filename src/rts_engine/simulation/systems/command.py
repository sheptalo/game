from __future__ import annotations

from dataclasses import dataclass

from rts_engine.core.commands import Command, CommandType
from rts_engine.simulation.world import World


@dataclass(frozen=True, slots=True)
class CommandSystem:
    def apply(self, world: World, commands: tuple[Command, ...]) -> None:
        for command in commands:
            if command.type is CommandType.MOVE:
                self._move(world, command)

    def _move(self, world: World, command: Command) -> None:
        if command.x is None or command.y is None:
            return
        for unit_id in command.units:
            if not world.units.has(unit_id):
                continue
            index = world.units.index(unit_id)
            if world.units.owner[index] != str(command.player_id):
                continue
            world.units.target_x[index] = command.x
            world.units.target_y[index] = command.y
