import { checksum, makeWorld, selectDefaultUnit } from "./simulation.js";

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
    resCurrent: document.querySelector("#res-current"),
  };
}

export function setStatus(ui, text, cls) {
  ui.status.textContent = text;
  ui.status.className = cls;
}

export function updateUi(ui, state) {
  ui.tick.textContent = String(state.simTick);
  ui.checksum.textContent = checksum(state);
  ui.selected.textContent = state.selectedUnit === null ? "none" : String(state.selectedUnit);
  ui.queued.textContent = String(state.queuedAcks);
  ui.resCurrent.textContent = String(state.world.resources[state.currentPlayer] ?? 0);
}

export function initPlayerOptions(ui, state) {
  ui.player.replaceChildren();
  for (let playerNumber = 1; playerNumber <= state.gameConfig.player_count; playerNumber += 1) {
    const option = document.createElement("option");
    option.value = `p${playerNumber}`;
    option.textContent = option.value;
    ui.player.appendChild(option);
  }
  ui.player.value = state.currentPlayer;
}

export function resetLocalWorld(state) {
  state.world = makeWorld(state.gameConfig);
  state.simTick = 0;
  state.lastVisualTickTime = performance.now();
  state.selectedUnit = null;
  state.queuedAcks = 0;
  selectDefaultUnit(state);
}
