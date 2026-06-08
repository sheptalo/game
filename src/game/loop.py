from __future__ import annotations

from dataclasses import dataclass, field

from config import SimulationConfig
from core.checksum import Checksum
from core.commands import CommandFrame
from core.types import Tick
from ecs.system import System
from game.systems import CommandSystem, default_systems
from game.world import World


@dataclass(slots=True)
class SimulationEngine:
    world: World
    config: SimulationConfig = field(default_factory=SimulationConfig)
    tick: Tick = Tick(0)
    command_system: CommandSystem = field(default_factory=CommandSystem)
    systems: tuple[type[System], ...] = field(default=default_systems)

    def step(self, frame: CommandFrame | None = None) -> Checksum | None:
        if frame is not None and int(frame.tick) != int(self.tick):
            raise ValueError(
                f"frame tick {int(frame.tick)} does not match simulation tick {int(self.tick)}"
            )

        commands = frame.commands if frame is not None else ()
        self.command_system.apply(self.world, commands)
        coordinator = self.world.coordinator
        for system_type in self.systems:
            coordinator.get_system(system_type).update(coordinator)

        checksum = None
        if int(self.tick) % self.config.checksum_interval == 0:
            checksum = Checksum(
                tick=int(self.tick), value=self.world.checksum(int(self.tick))
            )

        self.tick = Tick(int(self.tick) + 1)
        return checksum

    def run_until(
        self, target_tick: Tick, frames: dict[int, CommandFrame]
    ) -> list[Checksum]:
        checksums: list[Checksum] = []
        while int(self.tick) < int(target_tick):
            checksum = self.step(frames.get(int(self.tick)))
            if checksum is not None:
                checksums.append(checksum)
        return checksums
