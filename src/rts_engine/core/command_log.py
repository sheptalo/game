from __future__ import annotations

from dataclasses import dataclass, field

from rts_engine.core.commands import CommandFrame
from rts_engine.core.types import Tick
from rts_engine.simulation.engine import SimulationEngine


@dataclass(slots=True)
class CommandLog:
    frames: dict[int, CommandFrame] = field(default_factory=dict)

    def append(self, frame: CommandFrame) -> None:
        tick = int(frame.tick)
        if tick in self.frames:
            merged = self.frames[tick].commands + frame.commands
            self.frames[tick] = CommandFrame(tick=Tick(tick), commands=merged)
        else:
            self.frames[tick] = frame

    def replay(self, engine: SimulationEngine, until_tick: Tick) -> str:
        engine.run_until(until_tick, self.frames)
        return engine.world.checksum(int(engine.tick))
