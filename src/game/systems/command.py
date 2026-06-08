from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.commands import Command, CommandType
from ecs.coordinator import Coordinator
from game.components import Movement, Owner

if TYPE_CHECKING:
    from game.world import World


@dataclass(frozen=True, slots=True)
class CommandSystem:
    def apply(self, world: World, commands: tuple[Command, ...]) -> None:
        self.apply_to_coordinator(world.coordinator, commands)

    def apply_to_coordinator(
        self, coordinator: Coordinator, commands: tuple[Command, ...]
    ) -> None:
        for command in commands:
            if command.type is CommandType.MOVE:
                self._move(coordinator, command)

    def _move(self, coordinator: Coordinator, command: Command) -> None:
        if command.x is None or command.y is None:
            return
        for unit_id in command.units:
            entity = int(unit_id)
            if not coordinator.has_entity(entity):
                continue
            if not coordinator.has_component(
                entity, Owner
            ) or not coordinator.has_component(entity, Movement):
                continue
            if coordinator.get_component(entity, Owner).player_id != str(
                command.player_id
            ):
                continue
            movement = coordinator.get_component(entity, Movement)
            movement.target_x = command.x
            movement.target_y = command.y
