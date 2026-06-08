from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    tick_rate: int = 10
    checksum_interval: int = 100

    @property
    def tick_duration_seconds(self) -> float:
        return 1.0 / self.tick_rate


@dataclass(frozen=True, slots=True)
class MatchConfig:
    tick_rate: int = 10
    command_delay_ticks: int = 3
    max_commands_per_player_per_tick: int = 64
    snapshot_interval_ticks: int = 1000
    checksum_interval_ticks: int = 100


@dataclass(frozen=True, slots=True)
class InitialStateConfig:
    player_count: int = 101
    grid_columns: int = 11
    player_resources: int = 500
    spawn_start_x: int = 4000
    spawn_start_y: int = 4000
    spawn_step_x: int = 4000
    spawn_step_y: int = 4000
    unit_hp: int = 100
    unit_speed: int = 250


def game_config_payload(initial_state: InitialStateConfig) -> dict[str, Any]:
    return asdict(initial_state)
