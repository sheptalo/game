import { TILE_SIZE } from "./constants.js";
import { drawMap, worldToScreen } from "./map.js";
import { sortedUnits, unfixed } from "./simulation.js";

function visualAlpha(state) {
  const tickMs = 1000 / state.tickRate;
  return Math.min(1, Math.max(0, (performance.now() - state.lastVisualTickTime) / tickMs));
}

function lerp(from, to, alpha) {
  return from + (to - from) * alpha;
}

export function resizeCanvas(canvas, ctx) {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.floor(rect.width * ratio);
  canvas.height = Math.floor(rect.height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

export function renderFrame(ctx, canvas, state) {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  drawMap(ctx, state.camera, rect);

  const alpha = visualAlpha(state);
  for (const unit of sortedUnits(state.world)) {
    const position = worldToScreen(state.camera, unfixed(lerp(unit.px, unit.x, alpha)), unfixed(lerp(unit.py, unit.y, alpha)));
    const target = worldToScreen(state.camera, unfixed(unit.tx), unfixed(unit.ty));
    const mine = unit.owner === state.currentPlayer;

    ctx.strokeStyle = mine ? "#74f2ce" : "#ff8f70";
    ctx.globalAlpha = 0.45;
    ctx.beginPath();
    ctx.moveTo(position.x, position.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();
    ctx.globalAlpha = 1;

    ctx.fillStyle = mine ? "#3fd7b5" : "#ef6a4d";
    ctx.beginPath();
    ctx.arc(position.x, position.y, 11, 0, Math.PI * 2);
    ctx.fill();

    if (state.selectedUnit === unit.id) {
      ctx.strokeStyle = "#ffe082";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(position.x, position.y, 16, 0, Math.PI * 2);
      ctx.stroke();
      ctx.lineWidth = 1;
    }

    ctx.fillStyle = "#0b1020";
    ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.textAlign = "center";
    ctx.fillText(String(unit.id), position.x, position.y + 4);
  }
}
