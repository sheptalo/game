from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from rts_engine.config import SimulationConfig
from rts_engine.core.checksum import Checksum
from rts_engine.core.commands import CommandFrame
from rts_engine.core.types import Tick
from rts_engine.simulation.systems import CommandSystem, default_systems
from rts_engine.simulation.world import World


@dataclass(slots=True)
class SimulationEngine:
    world: World
    config: SimulationConfig = field(default_factory=SimulationConfig)
    tick: Tick = Tick(0)
    command_system: CommandSystem = field(default_factory=CommandSystem)
    systems: tuple[Callable[[World], None], ...] = field(default=default_systems)

    def step(self, frame: CommandFrame | None = None) -> Checksum | None:
        if frame is not None and int(frame.tick) != int(self.tick):
            raise ValueError(
                f"frame tick {int(frame.tick)} does not match simulation tick {int(self.tick)}"
            )

        commands = frame.commands if frame is not None else ()
        self.command_system.apply(self.world, commands)
        for system in self.systems:
            system(self.world)

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
