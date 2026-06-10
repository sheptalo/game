import { DEFAULT_CHECKSUM_INTERVAL_TICKS, DEFAULT_GAME_CONFIG, DEFAULT_TICK_RATE, SCALE } from "./constants.js";

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
  };
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

export function canonicalCommands(commands) {
  return [...commands].sort((a, b) => {
    const issuerA = Number(a.issuer ?? playerEntityId(a.player_id));
    const issuerB = Number(b.issuer ?? playerEntityId(b.player_id));
    if (issuerA !== issuerB) return issuerA - issuerB;
    if (a.sequence !== b.sequence) return a.sequence - b.sequence;
    return String(a.type).localeCompare(String(b.type));
  });
}

function commandIssuer(command) {
  return Number(command.issuer ?? playerEntityId(command.player_id));
}

function commandTargets(command) {
  return [...(command.targets ?? command.units ?? [])].map(Number).sort((a, b) => a - b);
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
    position.x += Math.trunc((dx * movement.speed) / dominant);
    position.y += Math.trunc((dy * movement.speed) / dominant);
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

  const frames = [...(message.command_frames ?? [])].sort((a, b) => Number(a.tick) - Number(b.tick));
  for (const frame of frames) {
    const frameTick = Number(frame.tick);
    while (state.simTick < frameTick) step(state, { commands: [] });
    step(state, frame);
  }
  while (state.simTick < Number(message.current_tick)) step(state, { commands: [] });
  state.lastVisualTickTime = performance.now();
}

function writeValue(addText, value) {
  if (typeof value === "number" && Number.isInteger(value)) {
    addText("s:int;");
    addText(`i:${value};`);
    return;
  }
  addText("s:str;");
  addText(`s:${String(value).length}:${String(value)};`);
}

function writeComponent(addText, name, payload) {
  addText(`s:${name.length}:${name};`);
  for (const field of Object.keys(payload).sort()) {
    addText(`s:${field.length}:${field};`);
    writeValue(addText, payload[field]);
  }
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

  addInt(state.simTick);
  addInt(state.snapshot.next_entity_id);
  for (const entity of sortedEntities(state.snapshot)) {
    addInt(entity.id);
    for (const componentName of Object.keys(entity).filter((key) => key !== "id").sort()) {
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
