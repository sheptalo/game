import { TILE_SIZE } from "./constants.js";
import { drawMap, worldToScreen } from "./map.js";
import { playerEntityId, units, unfixed, unitDirection, unitVisualPosition } from "./simulation.js";

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

function drawUnit(ctx, screenX, screenY, mine, direction) {
  const width = mine ? 18 : 14;
  const height = mine ? 28 : 22;
  const x = screenX - width / 2;
  const y = screenY - height;

  ctx.fillStyle = mine ? "#74f2ce" : "#ff8f70";
  ctx.fillRect(x, y, width, height);
  ctx.fillStyle = mine ? "#4ccca8" : "#d96f58";
  ctx.fillRect(x + 3, y + 6, width - 6, height - 10);

  if (direction.x !== 0 || direction.y !== 0) {
    const tipX = screenX + direction.x * 14;
    const tipY = screenY - height / 2 - direction.y * 14;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(screenX, screenY - height / 2);
    ctx.lineTo(tipX, tipY);
    ctx.stroke();
    ctx.lineWidth = 1;
  }
}

export function renderFrame(ctx, canvas, state) {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  drawMap(ctx, state.camera, rect);

  const alpha = visualAlpha(state);
  const issuer = playerEntityId(state.currentPlayer);
  for (const entity of units(state.snapshot)) {
    const position = unitVisualPosition(entity, alpha);
    const direction = unitDirection(entity);
    const screenPos = worldToScreen(state.camera, unfixed(position.x), unfixed(position.y), rect.height);
    const mine = entity.OwnedBy.owner === issuer;

    drawUnit(ctx, screenPos.x, screenPos.y, mine, direction);

    if (state.selectedUnit === entity.id) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.strokeRect(screenPos.x - 12, screenPos.y - 32, 24, 34);
      ctx.lineWidth = 1;
    }
  }
}
