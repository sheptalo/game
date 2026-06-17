import {
  collectObstacles,
  isGrounded,
  resolveAxis,
} from "./collision.js";
import { processTriggers, resetTriggerState } from "./triggers.js";
import {
  DEFAULT_CHECKSUM_INTERVAL_TICKS,
  DEFAULT_COMMAND_DELAY_TICKS,
  DEFAULT_GAME_CONFIG,
  DEFAULT_TICK_RATE,
  FALL_SPEED,
  JUMP_GRAVITY,
  JUMP_HEIGHT,
  JUMP_RISE_SPEED,
  MOVE_STEP,
  SPAWN_AIR_OFFSET,
  UNIT_COLLISION_HEIGHT,
  UNIT_COLLISION_WIDTH,
} from "./constants.js";

export function unfixed(value) {
  return value / 1000;
}

export function ownedUnit(snapshot, playerId) {
  return units(snapshot).find((candidate) => candidate.OwnedBy.owner === playerId) ?? null;
}

export function clampDirection(value) {
  return Math.max(-1, Math.min(1, Number(value)));
}

export function createGameState() {
  const gameConfig = { ...DEFAULT_GAME_CONFIG };
  return {
    ws: null,
    sequence: 1,
    playerId: null,
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
    lastSentDirection: "0",
    lastDirectionSendAt: 0,
    lastAutoResyncAt: 0,
    frameTimestamps: [],
    triggerEvents: [],
    particles: [],
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
  while (
    state.frameTimestamps.length > 0 &&
    state.frameTimestamps[0] < cutoff
  ) {
    state.frameTimestamps.shift();
  }
}

export function resetTpsCounter(state) {
  state.frameTimestamps = [];
}

function spawnPlatforms(entities, gameConfig, nextId) {
  const ceilingY = gameConfig.spawn_start_y + 550;
  const groundY =
    gameConfig.spawn_start_y -
    Math.floor(gameConfig.unit_collision_height / 2) -
    50;
  entities.push({
    id: nextId,
    Position: { x: gameConfig.spawn_start_x, y: groundY },
    Collision: { width: 8000, height: 100 },
  });
  nextId += 1;
  entities.push({
    id: nextId,
    Position: { x: gameConfig.spawn_start_x + 2000, y: ceilingY },
    Collision: { width: 800, height: 100 },
  });
  nextId += 1;
  entities.push({
    id: nextId,
    Position: { x: gameConfig.spawn_start_x, y: ceilingY },
    Collision: { width: 800, height: 100 },
  });
  nextId += 1;
  entities.push({
    id: nextId,
    Position: { x: gameConfig.spawn_start_x - 1000, y: ceilingY },
    Collision: { width: 100, height: 1500 },
    Trigger: { on_enter: "teleport", on_exit: "" },
  });
  nextId += 1;
  entities.push({
    id: nextId,
    Position: { x: gameConfig.spawn_start_x - 1000, y: -1000 },
    Collision: { width: 100000, height: 1 },
    Trigger: { on_enter: "spawn", on_exit: "" },
  });
  return nextId + 1;
}

export function makeSnapshot(gameConfig, source = null) {
  if (source) {
    return cloneSnapshot(source);
  }

  const entities = [];
  let nextId = 1;
  nextId = spawnPlatforms(entities, gameConfig, nextId);

  for (
    let playerNumber = 1;
    playerNumber <= gameConfig.player_count;
    playerNumber += 1
  ) {
    entities.push({ id: nextId });
    const playerId = nextId;
    nextId += 1;
    const column = (playerNumber - 1) % gameConfig.grid_columns;
    const row = Math.floor((playerNumber - 1) / gameConfig.grid_columns);
    const x = gameConfig.spawn_start_x + column * gameConfig.spawn_step_x;
    const airOffset = gameConfig.spawn_air_offset ?? SPAWN_AIR_OFFSET;
    const y =
      gameConfig.spawn_start_y + row * gameConfig.spawn_step_y + airOffset;
    entities.push({
      id: nextId,
      OwnedBy: { owner: playerId },
      Position: { x, y },
      Movement: { x: 0, y: 0 },
      Collision: {
        width: gameConfig.unit_collision_width ?? UNIT_COLLISION_WIDTH,
        height: gameConfig.unit_collision_height ?? UNIT_COLLISION_HEIGHT,
      },
      RigidBody: { vy: 0, jump_remaining: 0 },
      TriggerOverlap: { inside: [] },
    });
    nextId += 1;
  }

  return {
    next_entity_id: nextId,
    entities,
  };
}

function cloneSnapshot(snapshot) {
  return {
    next_entity_id: Number(snapshot.next_entity_id),
    entities: (snapshot.entities ?? []).map((entity) =>
      structuredClone(entity),
    ),
  };
}

export function sortedEntities(snapshot) {
  return [...snapshot.entities].sort((a, b) => a.id - b.id);
}

export function units(snapshot) {
  return sortedEntities(snapshot).filter((entity) => "OwnedBy" in entity);
}

export function collidables(snapshot) {
  return sortedEntities(snapshot).filter(
    (entity) => entity.Collision && entity.Position,
  );
}

export function unitPosition(entity) {
  return { x: entity.Position.x, y: entity.Position.y };
}

export function unitDirection(entity) {
  return { x: entity.Movement.x, y: entity.Movement.y };
}

function commandSortKey(command) {
  const type = String(command.type);
  const tie = type === "MOVE" ? clampDirection(command.x) : 0;
  return {
    issuer: Number(command.issuer),
    sequence: Number(command.sequence),
    type,
    targets: commandTargets(command),
    tie,
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
  return [...commands].sort((a, b) =>
    compareCommandKeys(commandSortKey(a), commandSortKey(b)),
  );
}

function commandTargets(command) {
  return [...command.targets].map(Number).sort((a, b) => a - b);
}

function snapshotComponentNames(entity) {
  return Object.keys(entity)
    .filter((key) => key !== "id" && /^[A-Z]/.test(key))
    .sort();
}

function applyCommands(state, commands) {
  for (const command of canonicalCommands(commands)) {
    const issuer = Number(command.issuer);
    if (command.type === "MOVE") {
      const directionX = clampDirection(command.x);
      for (const id of commandTargets(command)) {
        const entity = state.snapshot.entities.find(
          (candidate) => candidate.id === id,
        );
        if (
          !entity?.OwnedBy ||
          !entity.Movement ||
          entity.OwnedBy.owner !== issuer
        )
          continue;
        entity.Movement.x = directionX;
      }
      continue;
    }
    if (command.type !== "JUMP") continue;
    for (const id of commandTargets(command)) {
      const entity = state.snapshot.entities.find(
        (candidate) => candidate.id === id,
      );
      if (
        !entity?.OwnedBy ||
        !entity.Movement ||
        entity.OwnedBy.owner !== issuer
      )
        continue;
      entity.Movement.y = 1;
    }
  }
}

function processMovement(state) {
  const obstacles = collectObstacles(state.snapshot);
  const fallSpeed = state.gameConfig.fall_speed ?? FALL_SPEED;
  const jumpRiseSpeed = state.gameConfig.jump_rise_speed ?? JUMP_RISE_SPEED;
  const jumpGravity = state.gameConfig.jump_gravity ?? JUMP_GRAVITY;
  const movable = sortedEntities(state.snapshot).filter(
    (entity) =>
      entity.Position &&
      entity.Movement &&
      entity.Collision &&
      entity.RigidBody,
  );

  for (const entity of movable) {
    const position = entity.Position;
    const movement = entity.Movement;
    const collision = entity.Collision;
    const rigidbody = entity.RigidBody;

    if (movement.x !== 0) {
      position.x = resolveAxis(
        position,
        collision,
        obstacles,
        entity.id,
        "x",
        movement.x * MOVE_STEP,
      );
    }

    if (
      movement.y === 1 &&
      isGrounded(entity.id, position, collision, obstacles)
    ) {
      rigidbody.vy = jumpRiseSpeed;
    }
    movement.y = 0;

    if (rigidbody.vy > 0) {
      const oldY = position.y;
      position.y = resolveAxis(
        position, collision, obstacles, entity.id, "y", rigidbody.vy,
      );
      if (position.y === oldY) {
        rigidbody.vy = 0;
      } else {
        rigidbody.vy = Math.max(0, rigidbody.vy - jumpGravity);
      }
    } else if (!isGrounded(entity.id, position, collision, obstacles)) {
      rigidbody.vy = Math.max(-fallSpeed, rigidbody.vy - jumpGravity);
      position.y = resolveAxis(
        position, collision, obstacles, entity.id, "y", rigidbody.vy,
      );
    } else {
      rigidbody.vy = 0;
    }
  }
}

export function step(state, frame) {
  for (const entity of units(state.snapshot)) {
    entity._px = entity.Position.x;
    entity._py = entity.Position.y;
  }

  applyCommands(state, frame?.commands ?? []);
  processMovement(state);
  processTriggers(state);

  state.simTick += 1;
  state.lastVisualTickTime = performance.now();
}

export function bootstrapFromStateSync(state, message) {
  state.gameConfig = { ...DEFAULT_GAME_CONFIG, ...(message.game_config ?? {}) };
  state.playerId = message.player_id ?? null;
  resetTriggerState(state);
  state.snapshot = makeSnapshot(state.gameConfig, message.snapshot);
  state.simTick = Number(message.snapshot_tick ?? 0);
  state.tickRate = Number(message.tick_rate ?? DEFAULT_TICK_RATE);
  state.commandDelayTicks = Number(
    message.command_delay_ticks ?? DEFAULT_COMMAND_DELAY_TICKS,
  );
  state.checksumIntervalTicks = Number(
    message.checksum_interval_ticks ?? DEFAULT_CHECKSUM_INTERVAL_TICKS,
  );
  state.selectedUnit = null;
  state.queuedAcks = 0;
  state.lastSentDirection = "0";

  const snapshotTick = Number(message.snapshot_tick ?? 0);
  const currentTick = Number(message.current_tick ?? snapshotTick);
  const frames = [...(message.command_frames ?? [])].sort(
    (a, b) => Number(a.tick) - Number(b.tick),
  );
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

function formatListInside(inside) {
  const ids = [...(inside ?? [])].map(Number).sort((a, b) => a - b);
  if (ids.length === 0) return "[]";
  return `[${ids.join(", ")}]`;
}

function writeComponent(addText, name, payload) {
  addTaggedStr(addText, name);
  for (const field of Object.keys(payload).sort()) {
    addTaggedStr(addText, field);
    if (name === "TriggerOverlap" && field === "inside") {
      addTaggedStr(addText, "str");
      addTaggedStr(addText, formatListInside(payload[field]));
      continue;
    }
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
  const entity = state.snapshot.entities.find(
    (candidate) => candidate.id === state.selectedUnit,
  );
  if (!entity?.OwnedBy || entity.OwnedBy.owner !== state.playerId) return null;
  return entity;
}

export function selectDefaultUnit(state) {
  if (selectedOwnedUnit(state)) return;
  const entity = ownedUnit(state.snapshot, state.playerId);
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
