import { bindInput, focusCameraOnPlayer, updateCamera, updateKeyboardUnitMovement } from "./input.js";
import { encodeMessage, decodeMessage } from "./protocol.js";
import { renderFrame, resizeCanvas } from "./render.js";
import {
  bootstrapFromStateSync,
  checksum,
  clampDirection,
  createGameState,
  playerEntityId,
  recordSimFrame,
  resetTpsCounter,
  selectDefaultUnit,
  step,
} from "./simulation.js";
import { collectUi, initPlayerOptions, resetLocalWorld, setStatus, updateTps, updateUi } from "./ui.js";

export function createGame() {
  const canvas = document.querySelector("#game");
  const ctx = canvas.getContext("2d");
  const ui = collectUi();
  const state = createGameState();
  let focusCameraOnNextSync = false;

  function redrawUi() {
    updateUi(ui, state);
  }

  function sendCommand(command) {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
      setStatus(ui, "connect first", "bad");
      return;
    }
    state.ws.send(encodeMessage({ kind: "command", command }));
    state.queuedAcks += 1;
    redrawUi();
  }

  function sendDirection(unit, x, y) {
    sendCommand({
      type: "MOVE",
      issuer: playerEntityId(state.currentPlayer),
      sequence: state.sequence++,
      targets: [unit.id],
      x: clampDirection(x),
      y: clampDirection(y),
    });
  }

  function requestStateSync() {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return false;
    state.ws.send(encodeMessage({ kind: "state_sync_request" }));
    setStatus(ui, "resyncing", "warn");
    return true;
  }

  function desyncIncludesCurrentPlayer(report) {
    return Object.values(report.checksums ?? {}).some((players) => players.includes(state.currentPlayer));
  }

  function requestAutoResync(report) {
    if (!desyncIncludesCurrentPlayer(report)) return;
    const now = performance.now();
    if (now - state.lastAutoResyncAt < 1000) return;
    state.lastAutoResyncAt = now;
    requestStateSync();
  }

  function sendChecksumIfDue() {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
    if (state.checksumIntervalTicks <= 0) return;
    const completedTick = state.simTick - 1;
    if (completedTick <= 0 || completedTick % state.checksumIntervalTicks !== 0) return;
    state.ws.send(encodeMessage({
      kind: "checksum",
      player_id: state.currentPlayer,
      tick: completedTick,
      checksum: checksum(state, completedTick),
    }));
  }

  function advanceSimulation(frame) {
    const frameTick = Number(frame.tick);
    while (state.simTick < frameTick) {
      step(state, { commands: [] });
      sendChecksumIfDue();
    }
    step(state, frame);
    sendChecksumIfDue();
  }

  function connect() {
    if (state.ws) state.ws.close();
    resetTpsCounter(state);
    focusCameraOnNextSync = true;
    state.currentPlayer = ui.player.value;
    state.ws = new WebSocket(ui.url.value);
    state.ws.binaryType = "arraybuffer";
    setStatus(ui, "connecting", "warn");

    state.ws.addEventListener("open", () => setStatus(ui, "connected", "ok"));
    state.ws.addEventListener("close", () => setStatus(ui, "offline", "warn"));
    state.ws.addEventListener("error", () => setStatus(ui, "socket error", "bad"));
    state.ws.addEventListener("message", async (event) => {
      const message = await decodeMessage(event.data);
      if (message.kind === "state_sync") {
        bootstrapFromStateSync(state, message);
        initPlayerOptions(ui, state);
        selectDefaultUnit(state);
        if (focusCameraOnNextSync) {
          focusCameraOnPlayer(state, canvas);
          focusCameraOnNextSync = false;
        }
        setStatus(ui, "synced", "ok");
        redrawUi();
        return;
      }
      if (message.kind === "command_accepted") {
        state.queuedAcks = Math.max(0, state.queuedAcks - 1);
        redrawUi();
        return;
      }
      if (message.kind === "desync_report") {
        setStatus(ui, `desync at tick ${message.tick}`, "bad");
        console.warn("desync_report", message);
        requestAutoResync(message);
        return;
      }
      if (message.kind === "command_frame") {
        advanceSimulation(message);
        recordSimFrame(state);
        redrawUi();
      }
    });
  }

  function draw() {
    updateCamera(state, canvas);
    updateKeyboardUnitMovement(state, sendDirection);
    renderFrame(ctx, canvas, state);
    updateTps(ui, state);
    requestAnimationFrame(draw);
  }

  bindInput({ canvas, state, sendDirection, updateUi: redrawUi });

  ui.connect.addEventListener("click", connect);
  ui.reset.addEventListener("click", () => {
    resetLocalWorld(state);
    focusCameraOnPlayer(state, canvas);
    redrawUi();
  });
  ui.resync.addEventListener("click", requestStateSync);
  ui.player.addEventListener("change", () => {
    state.currentPlayer = ui.player.value;
    state.selectedUnit = null;
    selectDefaultUnit(state);
    focusCameraOnPlayer(state, canvas);
    redrawUi();
  });
  window.addEventListener("resize", () => resizeCanvas(canvas, ctx));

  resizeCanvas(canvas, ctx);
  initPlayerOptions(ui, state);
  selectDefaultUnit(state);
  focusCameraOnPlayer(state, canvas);
  redrawUi();
  draw();
}
