import { CAMERA_SPEED, DIRECTION_SEND_INTERVAL_MS, TILE_SIZE } from "./constants.js";
import { clampCamera } from "./map.js";
import { playerEntityId, selectedOwnedUnit, units, unfixed, unitPosition } from "./simulation.js";

function readDirection(keys) {
  let x = 0;
  let y = 0;
  if (keys.has("a")) x -= 1;
  if (keys.has("d")) x += 1;
  if (keys.has("w")) y += 1;
  if (keys.has("s")) y -= 1;
  return { x, y };
}

export function focusCameraOnPlayer(state, canvas) {
  const issuer = playerEntityId(state.currentPlayer);
  const entity = units(state.snapshot).find((candidate) => candidate.OwnedBy.owner === issuer);
  if (!entity) return;
  const pos = unitPosition(entity);
  const rect = canvas.getBoundingClientRect();
  state.camera.x = Math.max(0, unfixed(pos.x) * TILE_SIZE - rect.width / 2);
  state.camera.y = unfixed(pos.y) * TILE_SIZE - rect.height * 0.55;
  clampCamera(state.camera, rect);
}

export function updateCamera(state, canvas) {
  const issuer = playerEntityId(state.currentPlayer);
  const entity = units(state.snapshot).find((candidate) => candidate.OwnedBy.owner === issuer);
  if (entity) {
    const pos = unitPosition(entity);
    const rect = canvas.getBoundingClientRect();
    const targetX = Math.max(0, unfixed(pos.x) * TILE_SIZE - rect.width / 2);
    const targetY = unfixed(pos.y) * TILE_SIZE - rect.height * 0.55;
    state.camera.x += (targetX - state.camera.x) * 0.12;
    state.camera.y += (targetY - state.camera.y) * 0.12;
    clampCamera(state.camera, rect);
    return;
  }

  let dx = 0;
  let dy = 0;
  if (state.keys.has("arrowleft")) dx -= CAMERA_SPEED;
  if (state.keys.has("arrowright")) dx += CAMERA_SPEED;
  if (state.keys.has("arrowup")) dy -= CAMERA_SPEED;
  if (state.keys.has("arrowdown")) dy += CAMERA_SPEED;
  state.camera.x = Math.max(0, state.camera.x + dx);
  state.camera.y = Math.max(0, state.camera.y + dy);
  clampCamera(state.camera, canvas.getBoundingClientRect());
}

export function updateKeyboardUnitMovement(state, sendDirection) {
  const entity = selectedOwnedUnit(state);
  if (!entity) return;
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;

  const { x, y } = readDirection(state.keys);
  const directionKey = `${x},${y}`;
  if (directionKey === state.lastSentDirection) return;

  const now = performance.now();
  if (directionKey !== "0,0" && now - state.lastDirectionSendAt < DIRECTION_SEND_INTERVAL_MS) return;

  state.lastDirectionSendAt = now;
  state.lastSentDirection = directionKey;
  sendDirection(entity, x, y);
}

function inputKey(event) {
  if (event.code === "KeyW") return "w";
  if (event.code === "KeyA") return "a";
  if (event.code === "KeyS") return "s";
  if (event.code === "KeyD") return "d";
  if (event.code === "Space") return " ";
  if (event.code === "ArrowUp") return "arrowup";
  if (event.code === "ArrowDown") return "arrowdown";
  if (event.code === "ArrowLeft") return "arrowleft";
  if (event.code === "ArrowRight") return "arrowright";
  return event.key.toLowerCase();
}

export function bindInput({ canvas, state, sendDirection, updateUi }) {
  canvas.addEventListener("pointerdown", (event) => {
    if (event.button !== 1 && !state.keys.has(" ")) return;
    event.preventDefault();
    state.isPanning = true;
    state.lastPointer = { x: event.clientX, y: event.clientY };
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!state.isPanning || state.lastPointer === null) return;
    state.camera.x = Math.max(0, state.camera.x - (event.clientX - state.lastPointer.x));
    state.camera.y = Math.max(0, state.camera.y - (event.clientY - state.lastPointer.y));
    clampCamera(state.camera, canvas.getBoundingClientRect());
    state.lastPointer = { x: event.clientX, y: event.clientY };
  });

  canvas.addEventListener("pointerup", (event) => {
    if (!state.isPanning) return;
    state.isPanning = false;
    state.lastPointer = null;
    canvas.releasePointerCapture(event.pointerId);
  });

  const syncDirection = () => {
    state.lastSentDirection = "";
    updateKeyboardUnitMovement(state, sendDirection);
    updateUi();
  };

  window.addEventListener("keydown", (event) => {
    const key = inputKey(event);
    if ([" ", "arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d"].includes(key)) {
      event.preventDefault();
    }
    state.keys.add(key);
    if (["w", "a", "s", "d"].includes(key)) syncDirection();
  });

  window.addEventListener("keyup", (event) => {
    const key = inputKey(event);
    state.keys.delete(key);
    if (key === " ") {
      state.isPanning = false;
      state.lastPointer = null;
    }
    if (["w", "a", "s", "d"].includes(key)) syncDirection();
  });

  window.addEventListener("blur", () => {
    state.keys.clear();
    state.lastSentDirection = "";
    const entity = selectedOwnedUnit(state);
    if (entity) sendDirection(entity, 0, 0);
  });
}
