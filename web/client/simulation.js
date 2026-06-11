import {
  DEFAULT_CHECKSUM_INTERVAL_TICKS,
  DEFAULT_COMMAND_DELAY_TICKS,
  DEFAULT_GAME_CONFIG,
  DEFAULT_TICK_RATE,
  JUMP_HEIGHT,
  MOVE_STEP,
} from "./constants.js";

export function unfixed(value) {
  return value / 1000;
}

export function playerEntityId(slot) {
  return Number(String(slot).replace(/^p/, ""));
}

export function clampDirection(value) {
  return Math.max(-1, Math.min(1, Number(value)));
}

export function createGameState() {
  const gameConfig = { ...DEFAULT_GAME_CONFIG };
  return {
    ws: null,
    sequence: 1,
    currentPlayer: `p${gameConfig.player_count}`,
    selectedUnit: null,
    gameConfig,
    snapshot: makeSnapshot(gameConfig),
    simTick: 0,
    tickRate: DEFAULT_TICK_RATE,
    commandDelayTicks: DEFAULT_COMMAND_DELAY_TICKS,
    checksumIntervalTicks: DEFAULT_CHECKSUM_INTERVAL_TICKS,
    lastVisualTickTime: performance.now(),
    queuedAcks: 0,
    camera: { x: 0, y: 0 },
    keys: new Set(),
    isPanning: false,
    lastPointer: null,
    lastSentDirection: "0,0",
    lastDirectionSendAt: 0,
    lastAutoResyncAt: 0,
    frameTimestamps: [],
  };
}

const TPS_WINDOW_MS = 1000;

export function recordSimFrame(state) {
  const now = performance.now();
  state.frameTimestamps.push(now);
  pruneFrameTimestamps(state, now);
}

export function measuredTps(state, now = performance.now()) {
  pruneFrameTimestamps(state, now);
  return state.frameTimestamps.length;
}

function pruneFrameTimestamps(state, now) {
  const cutoff = now - TPS_WINDOW_MS;
  while (state.frameTimestamps.length > 0 && state.frameTimestamps[0] < cutoff) {
    state.frameTimestamps.shift();
  }
}

export function resetTpsCounter(state) {
  state.frameTimestamps = [];
}

export function makeSnapshot(gameConfig, source = null) {
  if (source) {
    return cloneSnapshot(source);
  }

  const entities = [];
  for (let playerNumber = 1; playerNumber <= gameConfig.player_count; playerNumber += 1) {
    entities.push({ id: playerNumber });
    const column = (playerNumber - 1) % gameConfig.grid_columns;
    const row = Math.floor((playerNumber - 1) / gameConfig.grid_columns);
    const x = gameConfig.spawn_start_x + column * gameConfig.spawn_step_x;
    const y = gameConfig.spawn_start_y + row * gameConfig.spawn_step_y;
    entities.push({
      id: gameConfig.player_count + playerNumber,
      OwnedBy: { owner: playerNumber },
      Position: { x, y },
      Movement: { x: 0, y: 0 },
    });
  }

  return {
    next_entity_id: gameConfig.player_count * 2 + 1,
    entities,
  };
}

function cloneSnapshot(snapshot) {
  return {
    next_entity_id: Number(snapshot.next_entity_id),
    entities: (snapshot.entities ?? []).map((entity) => structuredClone(entity)),
  };
}

export function sortedEntities(snapshot) {
  return [...snapshot.entities].sort((a, b) => a.id - b.id);
}

export function units(snapshot) {
  return sortedEntities(snapshot).filter((entity) => "OwnedBy" in entity);
}

export function unitPosition(entity) {
  return { x: entity.Position.x, y: entity.Position.y };
}

export function unitDirection(entity) {
  return { x: entity.Movement.x, y: entity.Movement.y };
}

function commandSortKey(command) {
  const x = clampDirection(command.x);
  const y = clampDirection(command.y);
  return {
    issuer: Number(command.issuer),
    sequence: Number(command.sequence),
    type: String(command.type),
    targets: commandTargets(command),
    tie: x ^ y,
  };
}

function compareCommandKeys(left, right) {
  if (left.issuer !== right.issuer) return left.issuer - right.issuer;
  if (left.sequence !== right.sequence) return left.sequence - right.sequence;
  if (left.type !== right.type) return left.type.localeCompare(right.type);
  if (left.targets.length !== right.targets.length) {
    return left.targets.length - right.targets.length;
  }
  for (let index = 0; index < left.targets.length; index += 1) {
    if (left.targets[index] !== right.targets[index]) {
      return left.targets[index] - right.targets[index];
    }
  }
  return left.tie - right.tie;
}

export function canonicalCommands(commands) {
  return [...commands].sort((a, b) => compareCommandKeys(commandSortKey(a), commandSortKey(b)));
}

function commandTargets(command) {
  return [...command.targets].map(Number).sort((a, b) => a - b);
}

function snapshotComponentNames(entity) {
  return Object.keys(entity).filter((key) => key !== "id" && /^[A-Z]/.test(key)).sort();
}

export function step(state, frame) {
  for (const entity of units(state.snapshot)) {
    entity._px = entity.Position.x;
    entity._py = entity.Position.y;
  }

  for (const command of canonicalCommands(frame?.commands ?? [])) {
    if (command.type !== "MOVE") continue;
    const issuer = Number(command.issuer);
    const directionX = clampDirection(command.x);
    const directionY = clampDirection(command.y);
    for (const id of commandTargets(command)) {
      const entity = state.snapshot.entities.find((candidate) => candidate.id === id);
      if (!entity?.OwnedBy || !entity.Movement || entity.OwnedBy.owner !== issuer) continue;
      entity.Movement.x = directionX;
      entity.Movement.y = directionY;
    }
  }

  for (const entity of units(state.snapshot)) {
    const position = entity.Position;
    const movement = entity.Movement;
    if (movement.x === 0 && movement.y === 0) continue;
    position.x += movement.x * MOVE_STEP;
    position.y += movement.y * JUMP_HEIGHT;
  }

  state.simTick += 1;
  state.lastVisualTickTime = performance.now();
}

export function bootstrapFromStateSync(state, message) {
  state.gameConfig = { ...DEFAULT_GAME_CONFIG, ...(message.game_config ?? {}) };
  state.snapshot = makeSnapshot(state.gameConfig, message.snapshot);
  state.simTick = Number(message.snapshot_tick ?? 0);
  state.tickRate = Number(message.tick_rate ?? DEFAULT_TICK_RATE);
  state.commandDelayTicks = Number(message.command_delay_ticks ?? DEFAULT_COMMAND_DELAY_TICKS);
  state.checksumIntervalTicks = Number(message.checksum_interval_ticks ?? DEFAULT_CHECKSUM_INTERVAL_TICKS);
  state.selectedUnit = null;
  state.queuedAcks = 0;
  state.lastSentDirection = "0,0";

  const snapshotTick = Number(message.snapshot_tick ?? 0);
  const currentTick = Number(message.current_tick ?? snapshotTick);
  const frames = [...(message.command_frames ?? [])].sort((a, b) => Number(a.tick) - Number(b.tick));
  if (snapshotTick >= currentTick && frames.length === 0) {
    state.simTick = currentTick;
  } else {
    for (const frame of frames) {
      const frameTick = Number(frame.tick);
      while (state.simTick < frameTick) step(state, { commands: [] });
      step(state, frame);
    }
    while (state.simTick < currentTick) step(state, { commands: [] });
  }
  state.lastVisualTickTime = performance.now();
}

function addTaggedStr(addText, value) {
  const text = String(value);
  addText(`s:${text.length}:${text};`);
}

function writeValue(addText, value) {
  if (typeof value === "boolean") {
    addTaggedStr(addText, "bool");
    addText(`i:${value ? 1 : 0};`);
    return;
  }
  if (typeof value === "number" && Number.isInteger(value)) {
    addTaggedStr(addText, "int");
    addText(`i:${value};`);
    return;
  }
  addTaggedStr(addText, "str");
  addTaggedStr(addText, String(value));
}

function writeComponent(addText, name, payload) {
  addTaggedStr(addText, name);
  for (const field of Object.keys(payload).sort()) {
    addTaggedStr(addText, field);
    writeValue(addText, payload[field]);
  }
}

export function checksum(state, tick = Math.max(0, state.simTick - 1)) {
  let hash = 2166136261;
  const addText = (text) => {
    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619) >>> 0;
    }
  };
  const addInt = (value) => addText(`i:${Number(value)};`);

  addInt(tick);
  addInt(state.snapshot.next_entity_id);
  for (const entity of sortedEntities(state.snapshot)) {
    addInt(entity.id);
    for (const componentName of snapshotComponentNames(entity)) {
      writeComponent(addText, componentName, entity[componentName]);
    }
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function selectedOwnedUnit(state) {
  if (state.selectedUnit === null) return null;
  const issuer = playerEntityId(state.currentPlayer);
  const entity = state.snapshot.entities.find((candidate) => candidate.id === state.selectedUnit);
  if (!entity?.OwnedBy || entity.OwnedBy.owner !== issuer) return null;
  return entity;
}

export function selectDefaultUnit(state) {
  if (selectedOwnedUnit(state)) return;
  const issuer = playerEntityId(state.currentPlayer);
  const entity = units(state.snapshot).find((candidate) => candidate.OwnedBy.owner === issuer);
  state.selectedUnit = entity?.id ?? null;
}

export function unitVisualPosition(entity, alpha) {
  const x = entity._px ?? entity.Position.x;
  const y = entity._py ?? entity.Position.y;
  return {
    x: x + (entity.Position.x - x) * alpha,
    y: y + (entity.Position.y - y) * alpha,
  };
}
