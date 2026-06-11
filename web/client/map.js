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
  ctx.fillStyle = '#07080f';
  ctx.fillRect(0, 0, rect.width, rect.height);

  const gridSize = 60;
  const ox = ((-(camera.x % gridSize)) + gridSize) % gridSize;
  const oy = ((-(camera.y % gridSize)) + gridSize) % gridSize;

  ctx.strokeStyle = 'rgba(0,255,224,0.03)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = ox - gridSize; x <= rect.width + gridSize; x += gridSize) {
    ctx.moveTo(x, 0);
    ctx.lineTo(x, rect.height);
  }
  for (let y = oy - gridSize; y <= rect.height + gridSize; y += gridSize) {
    ctx.moveTo(0, y);
    ctx.lineTo(rect.width, y);
  }
  ctx.stroke();
}
