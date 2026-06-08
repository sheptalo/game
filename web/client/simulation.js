import { DEFAULT_CHECKSUM_INTERVAL_TICKS, DEFAULT_GAME_CONFIG, DEFAULT_TICK_RATE, SCALE } from "./constants.js";

export function fixed(value) {
  return Math.round(value * SCALE);
}

export function unfixed(value) {
  return value / SCALE;
}

export function createGameState() {
  const gameConfig = { ...DEFAULT_GAME_CONFIG };
  return {
    ws: null,
    sequence: 1,
    currentPlayer: `p${gameConfig.player_count}`,
    selectedUnit: null,
    gameConfig,
    world: makeWorld(gameConfig),
    simTick: 0,
    tickRate: DEFAULT_TICK_RATE,
    checksumIntervalTicks: DEFAULT_CHECKSUM_INTERVAL_TICKS,
    lastVisualTickTime: performance.now(),
    queuedAcks: 0,
    camera: { x: 0, y: 0 },
    keys: new Set(),
    isPanning: false,
    lastPointer: null,
    lastUnitKeyMoveAt: 0,
    lastAutoResyncAt: 0,
  };
}

export function makeWorld(gameConfig, initialState = null) {
  if (initialState) {
    return {
      nextUnitId: Number(initialState.next_unit_id),
      resources: { ...initialState.resources },
      units: initialState.units.map((unit) => makeUnitFromState(unit)),
    };
  }

  const resources = {};
  const units = [];
  for (let playerNumber = 1; playerNumber <= gameConfig.player_count; playerNumber += 1) {
    const playerId = `p${playerNumber}`;
    const column = (playerNumber - 1) % gameConfig.grid_columns;
    const row = Math.floor((playerNumber - 1) / gameConfig.grid_columns);
    resources[playerId] = gameConfig.player_resources;
    units.push(
      makeUnitFromState({
        id: playerNumber,
        owner: playerId,
        x: gameConfig.spawn_start_x + column * gameConfig.spawn_step_x,
        y: gameConfig.spawn_start_y + row * gameConfig.spawn_step_y,
        hp: gameConfig.unit_hp,
        speed: gameConfig.unit_speed,
      })
    );
  }

  return {
    nextUnitId: gameConfig.player_count + 1,
    resources,
    units,
  };
}

export function makeUnitFromState(unit) {
  const x = Number(unit.x);
  const y = Number(unit.y);
  return {
    id: Number(unit.id),
    owner: String(unit.owner),
    x,
    y,
    px: x,
    py: y,
    tx: Number(unit.target_x ?? unit.x),
    ty: Number(unit.target_y ?? unit.y),
    hp: Number(unit.hp),
    speed: Number(unit.speed),
  };
}

export function sortedUnits(world) {
  return [...world.units].sort((a, b) => a.id - b.id);
}

export function canonicalCommands(commands) {
  return [...commands].sort((a, b) => {
    const ak = [a.player_id, a.sequence, a.type].join(":");
    const bk = [b.player_id, b.sequence, b.type].join(":");
    return ak.localeCompare(bk);
  });
}

export function step(state, frame) {
  for (const unit of sortedUnits(state.world)) {
    unit.px = unit.x;
    unit.py = unit.y;
  }

  for (const command of canonicalCommands(frame?.commands ?? [])) {
    if (command.type !== "MOVE") continue;
    const ids = [...(command.units ?? [])].sort((a, b) => a - b);
    for (const id of ids) {
      const unit = state.world.units.find((candidate) => candidate.id === id);
      if (!unit || unit.owner !== command.player_id) continue;
      unit.tx = command.x;
      unit.ty = command.y;
    }
  }

  for (const unit of sortedUnits(state.world)) {
    const dx = unit.tx - unit.x;
    const dy = unit.ty - unit.y;
    if (dx === 0 && dy === 0) continue;

    const distanceSq = dx * dx + dy * dy;
    if (distanceSq <= unit.speed * unit.speed) {
      unit.x = unit.tx;
      unit.y = unit.ty;
      continue;
    }

    const dominant = Math.max(Math.abs(dx), Math.abs(dy));
    unit.x += Math.trunc(dx * unit.speed / dominant);
    unit.y += Math.trunc(dy * unit.speed / dominant);
  }

  state.simTick += 1;
  state.lastVisualTickTime = performance.now();
}

export function bootstrapFromStateSync(state, message) {
  state.gameConfig = { ...DEFAULT_GAME_CONFIG, ...(message.game_config ?? {}) };
  state.world = makeWorld(state.gameConfig, message.snapshot ?? message.initial_state);
  state.simTick = Number(message.snapshot_tick ?? 0);
  state.tickRate = Number(message.tick_rate ?? DEFAULT_TICK_RATE);
  state.checksumIntervalTicks = Number(message.checksum_interval_ticks ?? DEFAULT_CHECKSUM_INTERVAL_TICKS);
  state.selectedUnit = null;
  state.queuedAcks = 0;

  const frames = [...(message.command_frames ?? [])].sort((a, b) => Number(a.tick) - Number(b.tick));
  for (const frame of frames) {
    const frameTick = Number(frame.tick);
    while (state.simTick < frameTick) step(state, { commands: [] });
    step(state, frame);
  }
  while (state.simTick < Number(message.current_tick)) step(state, { commands: [] });
  state.lastVisualTickTime = performance.now();
}

export function checksum(state) {
  let hash = 2166136261;
  const addText = (text) => {
    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
  };
  const addInt = (value) => addText(`i:${Number(value)};`);
  const addString = (value) => {
    const text = String(value);
    addText(`s:${text.length}:${text};`);
  };

  addInt(state.simTick);
  addInt(state.world.nextUnitId);
  for (const player of Object.keys(state.world.resources).sort()) {
    addString(player);
    addInt(state.world.resources[player]);
  }
  for (const unit of sortedUnits(state.world)) {
    addInt(unit.id);
    addString(unit.owner);
    addInt(unit.x);
    addInt(unit.y);
    addInt(unit.tx);
    addInt(unit.ty);
    addInt(unit.hp);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function selectedOwnedUnit(state) {
  if (state.selectedUnit === null) return null;
  const unit = state.world.units.find((candidate) => candidate.id === state.selectedUnit);
  if (!unit || unit.owner !== state.currentPlayer) return null;
  return unit;
}

export function selectDefaultUnit(state) {
  if (selectedOwnedUnit(state)) return;
  const unit = sortedUnits(state.world).find((candidate) => candidate.owner === state.currentPlayer);
  state.selectedUnit = unit?.id ?? null;
}
