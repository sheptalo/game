import { resetTriggerState } from "./triggers.js";
import { checksum, makeSnapshot, measuredTps, selectDefaultUnit } from "./simulation.js";

export function collectUi() {
  return {
    url: document.querySelector("#url"),
    player: document.querySelector("#player"),
    connect: document.querySelector("#connect"),
    reset: document.querySelector("#reset"),
    resync: document.querySelector("#resync"),
    status: document.querySelector("#status"),
    tick: document.querySelector("#tick"),
    checksum: document.querySelector("#checksum"),
    selected: document.querySelector("#selected"),
    queued: document.querySelector("#queued"),
    tps: document.querySelector("#tps"),
  };
}

export function setStatus(ui, text, cls) {
  ui.status.textContent = text.toUpperCase();
  ui.status.className = cls;
  ui.status.classList.remove('status-appear');
  void ui.status.offsetWidth; // force reflow so animation restarts
  ui.status.classList.add('status-appear');
}

export function updateTps(ui, state) {
  const tps = measuredTps(state);
  ui.tps.textContent = `${tps.toFixed(1)} / ${state.tickRate}`;
  ui.tps.className = tpsClass(tps, state.tickRate);
}

function tpsClass(tps, targetRate) {
  if (tps <= 0) return "";
  if (tps >= targetRate * 0.9) return "ok";
  if (tps >= targetRate * 0.5) return "warn";
  return "bad";
}

export function updateUi(ui, state) {
  ui.tick.textContent = String(state.simTick);
  ui.checksum.textContent = checksum(state);
  ui.selected.textContent  = state.selectedUnit === null ? '—' : String(state.selectedUnit);
  ui.queued.textContent = String(state.queuedAcks);
  updateTps(ui, state);
}

export function initPlayerOptions(ui, state) {
  ui.player.replaceChildren();
  for (let playerNumber = 1; playerNumber <= state.gameConfig.player_count; playerNumber += 1) {
    const option = document.createElement("option");
    option.value = `p${playerNumber}`;
    option.textContent = `P${playerNumber}`;
    ui.player.appendChild(option);
  }
  ui.player.value = state.currentPlayer;
}

export function resetLocalWorld(state) {
  state.snapshot = makeSnapshot(state.gameConfig);
  state.simTick = 0;
  state.lastVisualTickTime = performance.now();
  state.selectedUnit = null;
  state.queuedAcks = 0;
  state.frameTimestamps = [];
  state.lastSentDirection = "0,0";
  state.particles = [];
  resetTriggerState(state);
  selectDefaultUnit(state);
}
