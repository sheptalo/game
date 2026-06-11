export const SCALE = 1000;
export const DEFAULT_TICK_RATE = 10;
export const DEFAULT_COMMAND_DELAY_TICKS = 3;
export const DEFAULT_CHECKSUM_INTERVAL_TICKS = 100;

export const DEFAULT_GAME_CONFIG = {
  player_count: 1,
  grid_columns: 11,
  spawn_start_x: 4000,
  spawn_start_y: 4000,
  spawn_step_x: 4000,
  spawn_step_y: 4000,
  unit_collision_width: 100,
  unit_collision_height: 200,
  move_step: 100,
  jump_height: 1000,
  jump_rise_speed: 100,
  fall_speed: 100,
  spawn_air_offset: 800,
};

export const MOVE_STEP = DEFAULT_GAME_CONFIG.move_step;
export const JUMP_HEIGHT = DEFAULT_GAME_CONFIG.jump_height;
export const JUMP_RISE_SPEED = DEFAULT_GAME_CONFIG.jump_rise_speed;
export const FALL_SPEED = DEFAULT_GAME_CONFIG.fall_speed;
export const SPAWN_AIR_OFFSET = DEFAULT_GAME_CONFIG.spawn_air_offset;
export const UNIT_COLLISION_WIDTH = DEFAULT_GAME_CONFIG.unit_collision_width;
export const UNIT_COLLISION_HEIGHT = DEFAULT_GAME_CONFIG.unit_collision_height;

export const TILE_SIZE = 24;
export const CAMERA_SPEED = 18;
export const DIRECTION_SEND_INTERVAL_MS = 50;

export const MAP_WIDTH = 52;
export const MAP_HEIGHT = 48;
