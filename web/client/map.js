import { MAP_HEIGHT, MAP_WIDTH, TILE_SIZE } from "./constants.js";

export function clampCamera(camera, rect) {
  camera.x = Math.max(0, Math.min(camera.x, MAP_WIDTH * TILE_SIZE - rect.width));
  const maxY = MAP_HEIGHT * TILE_SIZE - rect.height;
  camera.y = Math.max(-maxY, Math.min(camera.y, maxY));
}

export function worldToScreen(camera, x, y, viewHeight = 0) {
  return {
    x: x * TILE_SIZE - camera.x,
    y: viewHeight - y * TILE_SIZE + camera.y,
  };
}

function groundHeight(tileX) {
  const wave = Math.sin(tileX * 0.35) * 1.8 + Math.cos(tileX * 0.12) * 1.2;
  return 3 + Math.round(wave);
}

function terrainColor(tileX, groundY, tileY) {
  if (tileY > groundY) {
    const depth = tileY - groundY;
    return depth > 4 ? "#03152b" : "#0b5260";
  }
  if (tileY === groundY) return tileX % 2 === 0 ? "#8b6d43" : "#9c7a4d";
  if (tileY >= groundY - 2) return tileX % 2 === 0 ? "#2f7d48" : "#378b50";
  return tileY % 2 === 0 ? "#5aa0e6" : "#4f94d9";
}

export function drawMap(ctx, camera, rect) {
  const gradient = ctx.createLinearGradient(0, 0, 0, rect.height);
  gradient.addColorStop(0, "#173a63");
  gradient.addColorStop(0.55, "#4f94d9");
  gradient.addColorStop(1, "#8fd0ff");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, rect.width, rect.height);

  const startX = Math.floor(camera.x / TILE_SIZE) - 1;
  const endX = Math.ceil((camera.x + rect.width) / TILE_SIZE) + 1;
  const startY = 0;
  const endY = MAP_HEIGHT;

  for (let tileX = startX; tileX <= endX; tileX += 1) {
    const groundY = groundHeight(tileX);
    for (let tileY = startY; tileY <= endY; tileY += 1) {
      const screen = worldToScreen(camera, tileX, tileY, rect.height);
      if (screen.x + TILE_SIZE < 0 || screen.x > rect.width) continue;
      if (screen.y + TILE_SIZE < 0 || screen.y > rect.height) continue;
      ctx.fillStyle = terrainColor(tileX, groundY, tileY);
      ctx.fillRect(screen.x, screen.y, TILE_SIZE + 1, TILE_SIZE + 1);
    }
  }
}
