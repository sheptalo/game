import {
  DEEP_WATER_BORDER,
  ISLAND_CENTER_X,
  ISLAND_CENTER_Y,
  ISLAND_RADIUS,
  MAP_HEIGHT,
  MAP_WIDTH,
  TILE_SIZE,
} from "./constants.js";

export function clampCamera(camera, rect) {
  camera.x = Math.max(0, Math.min(camera.x, MAP_WIDTH * TILE_SIZE - rect.width));
  camera.y = Math.max(0, Math.min(camera.y, MAP_HEIGHT * TILE_SIZE - rect.height));
}

export function worldToScreen(camera, x, y) {
  return {
    x: x * TILE_SIZE - camera.x,
    y: y * TILE_SIZE - camera.y,
  };
}

export function screenToWorld(camera, canvas, event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left + camera.x) / TILE_SIZE,
    y: (event.clientY - rect.top + camera.y) / TILE_SIZE,
  };
}

export function clampWorldX(x) {
  return Math.max(0, Math.min(MAP_WIDTH - 0.001, x));
}

export function clampWorldY(y) {
  return Math.max(0, Math.min(MAP_HEIGHT - 0.001, y));
}

function terrainAt(tileX, tileY) {
  if (
    tileX < 0 ||
    tileY < 0 ||
    tileX >= MAP_WIDTH ||
    tileY >= MAP_HEIGHT ||
    tileX < DEEP_WATER_BORDER ||
    tileY < DEEP_WATER_BORDER ||
    tileX >= MAP_WIDTH - DEEP_WATER_BORDER ||
    tileY >= MAP_HEIGHT - DEEP_WATER_BORDER
  ) {
    return "deep_water";
  }

  const dx = (tileX + 0.5 - ISLAND_CENTER_X) / ISLAND_RADIUS;
  const dy = (tileY + 0.5 - ISLAND_CENTER_Y) / (ISLAND_RADIUS * 0.82);
  const wobble = Math.sin(tileX * 0.73 + tileY * 0.31) * 0.055 + Math.cos(tileX * 0.19 - tileY * 0.67) * 0.035;
  const distance = Math.sqrt(dx * dx + dy * dy) + wobble;

  if (distance > 1.08) return "deep_water";
  if (distance > 0.98) return "shallow_water";
  if (distance > 0.90) return "beach";
  if (distance > 0.70) return "grass";
  return "highland";
}

function terrainColor(terrain, tileX, tileY) {
  const noise = Math.sin(tileX * 12.9898 + tileY * 78.233) * 43758.5453;
  const variant = Math.abs(noise - Math.floor(noise));
  if (terrain === "deep_water") return variant > 0.5 ? "#03152b" : "#041b35";
  if (terrain === "shallow_water") return variant > 0.5 ? "#0b5260" : "#0d6170";
  if (terrain === "beach") return variant > 0.5 ? "#b99f61" : "#d0b876";
  if (terrain === "grass") return variant > 0.5 ? "#2f7d48" : "#378b50";
  return variant > 0.5 ? "#24663d" : "#2a7042";
}

export function drawMap(ctx, camera, rect) {
  const startX = Math.floor(camera.x / TILE_SIZE) - 1;
  const startY = Math.floor(camera.y / TILE_SIZE) - 1;
  const endX = Math.ceil((camera.x + rect.width) / TILE_SIZE) + 1;
  const endY = Math.ceil((camera.y + rect.height) / TILE_SIZE) + 1;

  for (let tileY = startY; tileY <= endY; tileY += 1) {
    for (let tileX = startX; tileX <= endX; tileX += 1) {
      const terrain = terrainAt(tileX, tileY);
      const screen = worldToScreen(camera, tileX, tileY);
      ctx.fillStyle = terrainColor(terrain, tileX, tileY);
      ctx.fillRect(screen.x, screen.y, TILE_SIZE, TILE_SIZE);
      ctx.strokeStyle = ctx.fillStyle;
      ctx.strokeRect(screen.x, screen.y, TILE_SIZE, TILE_SIZE);
    }
  }
}
