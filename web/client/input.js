import { CAMERA_SPEED, TILE_SIZE, UNIT_KEY_MOVE_DISTANCE, UNIT_KEY_MOVE_INTERVAL_MS } from "./constants.js";
import { clampCamera, clampWorldX, clampWorldY, screenToWorld } from "./map.js";
import { selectedOwnedUnit, sortedUnits, unfixed } from "./simulation.js";

function pickUnit(state, position) {
  const candidates = sortedUnits(state.world).filter((unit) => unit.owner === state.currentPlayer);
  for (const unit of candidates) {
    const dx = unfixed(unit.x) - position.x;
    const dy = unfixed(unit.y) - position.y;
    if (dx * dx + dy * dy < 0.7) return unit;
  }
  return null;
}

export function focusCameraOnPlayer(state, canvas) {
  const unit = sortedUnits(state.world).find((candidate) => candidate.owner === state.currentPlayer);
  if (!unit) return;
  const rect = canvas.getBoundingClientRect();
  state.camera.x = Math.max(0, unfixed(unit.x) * TILE_SIZE - rect.width / 2);
  state.camera.y = Math.max(0, unfixed(unit.y) * TILE_SIZE - rect.height / 2);
  clampCamera(state.camera, rect);
}

export function updateCamera(state, canvas) {
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

export function updateKeyboardUnitMovement(state, sendMove) {
  const unit = selectedOwnedUnit(state);
  if (!unit) return;
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;

  let dx = 0;
  let dy = 0;
  if (state.keys.has("a")) dx -= 1;
  if (state.keys.has("d")) dx += 1;
  if (state.keys.has("w")) dy -= 1;
  if (state.keys.has("s")) dy += 1;
  if (dx === 0 && dy === 0) return;

  const now = performance.now();
  if (now - state.lastUnitKeyMoveAt < UNIT_KEY_MOVE_INTERVAL_MS) return;
  state.lastUnitKeyMoveAt = now;

  const length = Math.max(1, Math.hypot(dx, dy));
  const x = unfixed(unit.x) + (dx / length) * UNIT_KEY_MOVE_DISTANCE;
  const y = unfixed(unit.y) + (dy / length) * UNIT_KEY_MOVE_DISTANCE;
  sendMove(unit, clampWorldX(x), clampWorldY(y));
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

export function bindInput({ canvas, state, sendMove, updateUi }) {
  canvas.addEventListener("click", (event) => {
    const unit = pickUnit(state, screenToWorld(state.camera, canvas, event));
    state.selectedUnit = unit?.id ?? null;
    updateUi();
  });

  canvas.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    const unit = selectedOwnedUnit(state);
    if (!unit) return;
    const position = screenToWorld(state.camera, canvas, event);
    sendMove(unit, clampWorldX(position.x), clampWorldY(position.y));
  });

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

  window.addEventListener("keydown", (event) => {
    const key = inputKey(event);
    if ([" ", "arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d"].includes(key)) {
      event.preventDefault();
    }
    state.keys.add(key);
  });

  window.addEventListener("keyup", (event) => {
    const key = inputKey(event);
    state.keys.delete(key);
    if (key === " ") {
      state.isPanning = false;
      state.lastPointer = null;
    }
  });
}
