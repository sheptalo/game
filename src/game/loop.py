from __future__ import annotations

from dataclasses import dataclass, field

import esper

from config import SimulationConfig
from core.checksum import Checksum, checksum_snapshot
from core.commands import CommandFrame
from core.types import Tick
from game.systems import CommandSystem
from game.world import World


@dataclass(slots=True)
class SimulationEngine:
    world: World
    config: SimulationConfig = field(default_factory=SimulationConfig)
    tick: Tick = Tick(0)
    command_system: CommandSystem = field(default_factory=CommandSystem)

    def step(self, frame: CommandFrame | None = None) -> Checksum | None:
        if frame is not None and int(frame.tick) != int(self.tick):
            raise ValueError(
                f"frame tick {int(frame.tick)} does not match simulation tick {int(self.tick)}"
            )

        with self.world.bind():
            self.command_system.apply(frame.commands if frame is not None else ())
            esper.process()

        checksum = None
        if int(self.tick) % self.config.checksum_interval == 0:
            checksum = Checksum(
                tick=int(self.tick),
                value=checksum_snapshot(int(self.tick), self.world.to_snapshot()),
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

    def state_checksum(self) -> str:
        return checksum_snapshot(int(self.tick), self.world.to_snapshot())
