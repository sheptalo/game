import { TILE_SIZE } from "./constants.js";
import { drawMap, worldToScreen } from "./map.js";
import { playerEntityId, units, unfixed, unitRenderTarget, unitVisualPosition } from "./simulation.js";

function visualAlpha(state) {
  const tickMs = 1000 / state.tickRate;
  return Math.min(1, Math.max(0, (performance.now() - state.lastVisualTickTime) / tickMs));
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
  const issuer = playerEntityId(state.currentPlayer);
  for (const entity of units(state.snapshot)) {
    const position = unitVisualPosition(entity, alpha);
    const target = unitRenderTarget(entity);
    const screenPos = worldToScreen(state.camera, unfixed(position.x), unfixed(position.y));
    const screenTarget = worldToScreen(state.camera, unfixed(target.x), unfixed(target.y));
    const mine = entity.OwnedBy.owner === issuer;

    ctx.strokeStyle = mine ? "#74f2ce" : "#ff8f70";
    ctx.globalAlpha = 0.45;
    ctx.beginPath();
    ctx.moveTo(screenPos.x, screenPos.y);
    ctx.lineTo(screenTarget.x, screenTarget.y);
    ctx.stroke();
    ctx.globalAlpha = 1;

    ctx.fillStyle = mine ? "#74f2ce" : "#ff8f70";
    ctx.beginPath();
    ctx.arc(screenPos.x, screenPos.y, mine ? 7 : 5, 0, Math.PI * 2);
    ctx.fill();

    if (state.selectedUnit === entity.id) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(screenPos.x, screenPos.y, 10, 0, Math.PI * 2);
      ctx.stroke();
      ctx.lineWidth = 1;
    }
  }
}
