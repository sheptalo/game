import { TILE_SIZE } from "./constants.js";
import { drawMap, worldToScreen } from "./map.js";
import {
  collidables,
  resolveIssuer,
  units,
  unfixed,
  unitDirection,
  unitVisualPosition,
} from "./simulation.js";

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

function drawPlatform(ctx, entity, camera, viewHeight) {
  const { width, height } = entity.Collision;
  const center = worldToScreen(camera, unfixed(entity.Position.x), unfixed(entity.Position.y), viewHeight);
  const screenW = unfixed(width) * TILE_SIZE;
  const screenH = unfixed(height) * TILE_SIZE;
  const x = center.x - screenW / 2;
  const y = center.y - screenH / 2;

  if (entity.Trigger) {
    ctx.fillStyle = "rgba(116, 242, 206, 0.18)";
    ctx.fillRect(x, y, screenW, screenH);
    ctx.strokeStyle = "rgba(116, 242, 206, 0.75)";
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(x, y, screenW, screenH);
    ctx.setLineDash([]);
    return;
  }

  const isCeiling = entity.Position.y > 4200;
  ctx.fillStyle = isCeiling ? "#6b5344" : "#8b6d43";
  ctx.fillRect(x, y, screenW, screenH);
  ctx.strokeStyle = isCeiling ? "#4a382d" : "#5c472f";
  ctx.strokeRect(x, y, screenW, screenH);
}

function drawUnit(ctx, screenX, screenY, mine, direction, collision) {
  const screenW = unfixed(collision.width) * TILE_SIZE;
  const screenH = unfixed(collision.height) * TILE_SIZE;
  const x = screenX - screenW / 2;
  const y = screenY - screenH / 2;

  ctx.fillStyle = mine ? "#74f2ce" : "#ff8f70";
  ctx.fillRect(x, y, screenW, screenH);
  ctx.fillStyle = mine ? "#4ccca8" : "#d96f58";
  ctx.fillRect(x + 4, y + 8, screenW - 8, screenH - 14);

  if (direction.x !== 0) {
    const tipX = screenX + direction.x * 16;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(screenX, screenY - screenH / 2);
    ctx.lineTo(tipX, screenY - screenH / 2);
    ctx.stroke();
    ctx.lineWidth = 1;
  }
}

export function renderFrame(ctx, canvas, state) {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  drawMap(ctx, state.camera, rect);

  for (const entity of collidables(state.snapshot)) {
    if ("OwnedBy" in entity) continue;
    drawPlatform(ctx, entity, state.camera, rect.height);
  }

  const alpha = visualAlpha(state);
  const issuer = resolveIssuer(state.snapshot, state.currentPlayer);
  for (const entity of units(state.snapshot)) {
    const position = unitVisualPosition(entity, alpha);
    const direction = unitDirection(entity);
    const screenPos = worldToScreen(
      state.camera,
      unfixed(position.x),
      unfixed(position.y),
      rect.height,
    );
    const mine = entity.OwnedBy.owner === issuer;

    drawUnit(ctx, screenPos.x, screenPos.y, mine, direction, entity.Collision);

    if (state.selectedUnit === entity.id) {
      const screenW = unfixed(entity.Collision.width) * TILE_SIZE;
      const screenH = unfixed(entity.Collision.height) * TILE_SIZE;
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1;
      ctx.strokeRect(
        screenPos.x - screenW / 2 - 2,
        screenPos.y - screenH / 2 - 2,
        screenW + 4,
        screenH + 4,
      );
      ctx.lineWidth = 1;
    }
  }
}
