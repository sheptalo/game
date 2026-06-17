import { CAMERA_SPEED, DIRECTION_SEND_INTERVAL_MS, TILE_SIZE } from "./constants.js";
import { clampCamera } from "./map.js";
import { ownedUnit, selectedOwnedUnit, unfixed, unitPosition } from "./simulation.js";

function readMoveX(keys) {
  let x = 0;
  if (keys.has("a")) x -= 1;
  if (keys.has("d")) x += 1;
  return x;
}

export function focusCameraOnPlayer(state, canvas) {
  const entity = ownedUnit(state.snapshot, state.playerId);
  if (!entity) return;
  const pos = unitPosition(entity);
  const rect = canvas.getBoundingClientRect();
  state.camera.x = Math.max(0, unfixed(pos.x) * TILE_SIZE - rect.width / 2);
  state.camera.y = unfixed(pos.y) * TILE_SIZE - rect.height * 0.55;
  clampCamera(state.camera, rect);
}

export function updateCamera(state, canvas) {
  const entity = ownedUnit(state.snapshot, state.playerId);
  if (entity) {
    const pos = unitPosition(entity);
    const rect = canvas.getBoundingClientRect();
    const targetX = Math.max(0, unfixed(pos.x) * TILE_SIZE - rect.width / 2);
    // const targetY = unfixed(pos.y) * TILE_SIZE - rect.height * 0.55;
    state.camera.x += (targetX - state.camera.x) * 0.12;
    // state.camera.y += (targetY - state.camera.y) * 0.12;
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

export function updateKeyboardUnitMovement(state, sendMove) {
  const entity = selectedOwnedUnit(state);
  if (!entity) return;
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;

  const x = readMoveX(state.keys);
  const directionKey = String(x);
  if (directionKey === state.lastSentDirection) return;

  const now = performance.now();
  if (directionKey !== "0" && now - state.lastDirectionSendAt < DIRECTION_SEND_INTERVAL_MS) return;

  state.lastDirectionSendAt = now;
  state.lastSentDirection = directionKey;
  sendMove(entity, x);
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

export function bindInput({ canvas, state, sendMove, sendJump, updateUi }) {
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

  const syncMove = () => {
    state.lastSentDirection = "";
    updateKeyboardUnitMovement(state, sendMove);
    updateUi();
  };

  window.addEventListener("keydown", (event) => {
    if (event.target.tagName === "INPUT") return;
    const key = inputKey(event);
    if ([" ", "arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d"].includes(key)) {
      event.preventDefault();
    }
    if (key === "w" && !state.keys.has("w")) {
      const entity = selectedOwnedUnit(state);
      if (entity) sendJump(entity);
    }
    state.keys.add(key);
    if (key === "a" || key === "d") syncMove();
  });

  window.addEventListener("keyup", (event) => {
    if (event.target.tagName === "INPUT") return;
    const key = inputKey(event);
    state.keys.delete(key);
    if (key === " ") {
      state.isPanning = false;
      state.lastPointer = null;
    }
    if (key === "a" || key === "d") syncMove();
  });

  window.addEventListener("blur", () => {
    state.keys.clear();
    state.lastSentDirection = "";
    const entity = selectedOwnedUnit(state);
    if (entity) sendMove(entity, 0);
  });
}
