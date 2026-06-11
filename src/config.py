from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MatchConfig:
    tick_rate: int = 20
    command_delay_ticks: int = 3
    snapshot_interval_ticks: int = 1000
    checksum_interval_ticks: int = 100


@dataclass(frozen=True, slots=True)
class InitialStateConfig:
    player_count: int = 1
    grid_columns: int = 11
    spawn_start_x: int = 4000
    spawn_start_y: int = 4000
    spawn_step_x: int = 4000
    spawn_step_y: int = 4000
    unit_collision_width: int = 100
    unit_collision_height: int = 200
    move_step: int = 100
    jump_height: int = 1000
    jump_rise_speed: int = 100
    fall_speed: int = 100
    spawn_air_offset: int = 800
