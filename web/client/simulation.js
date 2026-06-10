import { DEFAULT_CHECKSUM_INTERVAL_TICKS, DEFAULT_GAME_CONFIG, DEFAULT_TICK_RATE, SCALE } from "./constants.js";

const SNAPSHOT_COMPONENTS = ["Movement", "OwnedBy", "Position", "Resources"];

export function fixed(value) {
  return Math.round(value * SCALE);
}

export function unfixed(value) {
  return value / SCALE;
}

export function playerEntityId(slot) {
  return Number(String(slot).replace(/^p/, ""));
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
    checksumIntervalTicks: DEFAULT_CHECKSUM_INTERVAL_TICKS,
    lastVisualTickTime: performance.now(),
    queuedAcks: 0,
    camera: { x: 0, y: 0 },
    keys: new Set(),
    isPanning: false,
    lastPointer: null,
    lastUnitKeyMoveAt: 0,
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
    entities.push({ id: playerNumber, Resources: { amount: gameConfig.player_resources } });
    const column = (playerNumber - 1) % gameConfig.grid_columns;
    const row = Math.floor((playerNumber - 1) / gameConfig.grid_columns);
    const x = gameConfig.spawn_start_x + column * gameConfig.spawn_step_x;
    const y = gameConfig.spawn_start_y + row * gameConfig.spawn_step_y;
    entities.push({
      id: gameConfig.player_count + playerNumber,
      OwnedBy: { owner: playerNumber },
      Position: { x, y },
      Movement: { target_x: x, target_y: y, speed: gameConfig.unit_speed },
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

export function playerResources(snapshot, playerSlot) {
  const playerId = playerEntityId(playerSlot);
  const player = snapshot.entities.find((entity) => entity.id === playerId);
  return player?.Resources?.amount ?? 0;
}

export function unitPosition(entity) {
  return { x: entity.Position.x, y: entity.Position.y };
}

export function unitTarget(entity) {
  return { x: entity.Movement.target_x, y: entity.Movement.target_y };
}

function commandSortKey(command) {
  const issuer = Number(command.issuer ?? playerEntityId(command.player_id));
  const x = Number(command.x ?? 0);
  const y = Number(command.y ?? 0);
  return {
    issuer,
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

function commandIssuer(command) {
  return Number(command.issuer ?? playerEntityId(command.player_id));
}

function commandTargets(command) {
  return [...(command.targets ?? command.units ?? [])].map(Number).sort((a, b) => a - b);
}

function truncDiv(numerator, denominator) {
  if (numerator < 0) return -Math.trunc((-numerator) / denominator);
  return Math.trunc(numerator / denominator);
}

export function step(state, frame) {
  for (const entity of units(state.snapshot)) {
    entity._px = entity.Position.x;
    entity._py = entity.Position.y;
  }

  for (const command of canonicalCommands(frame?.commands ?? [])) {
    if (command.type !== "MOVE") continue;
    const issuer = commandIssuer(command);
    for (const id of commandTargets(command)) {
      const entity = state.snapshot.entities.find((candidate) => candidate.id === id);
      if (!entity?.OwnedBy || entity.OwnedBy.owner !== issuer) continue;
      entity.Movement.target_x = command.x;
      entity.Movement.target_y = command.y;
    }
  }

  for (const entity of units(state.snapshot)) {
    const position = entity.Position;
    const movement = entity.Movement;
    const dx = movement.target_x - position.x;
    const dy = movement.target_y - position.y;
    if (dx === 0 && dy === 0) continue;

    const distanceSq = dx * dx + dy * dy;
    if (distanceSq <= movement.speed * movement.speed) {
      position.x = movement.target_x;
      position.y = movement.target_y;
      continue;
    }

    const dominant = Math.max(Math.abs(dx), Math.abs(dy));
    position.x += truncDiv(dx * movement.speed, dominant);
    position.y += truncDiv(dy * movement.speed, dominant);
  }

  state.simTick += 1;
  state.lastVisualTickTime = performance.now();
}

export function bootstrapFromStateSync(state, message) {
  state.gameConfig = { ...DEFAULT_GAME_CONFIG, ...(message.game_config ?? {}) };
  state.snapshot = makeSnapshot(state.gameConfig, message.snapshot);
  state.simTick = Number(message.snapshot_tick ?? 0);
  state.tickRate = Number(message.tick_rate ?? DEFAULT_TICK_RATE);
  state.checksumIntervalTicks = Number(message.checksum_interval_ticks ?? DEFAULT_CHECKSUM_INTERVAL_TICKS);
  state.selectedUnit = null;
  state.queuedAcks = 0;

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
    for (const componentName of SNAPSHOT_COMPONENTS) {
      if (!(componentName in entity)) continue;
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

export function unitRenderTarget(entity) {
  return unitTarget(entity);
}
