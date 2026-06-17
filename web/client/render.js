import { TILE_SIZE } from "./constants.js";
import { drawMap, worldToScreen } from "./map.js";
import {
  collidables,
  units,
  unfixed,
  unitDirection,
  unitVisualPosition,
} from "./simulation.js";

const CYAN    = '#00ffe0';
const BLUE    = '#006eff';
const MAGENTA = '#ff00c8';
const PURPLE  = '#a000ff';

// Visual minimum sizes so units are visible at any scale
const MIN_UNIT_W = 8;
const MIN_UNIT_H = 14;

function visualAlpha(state) {
  const tickMs = 1000 / state.tickRate;
  return Math.min(1, Math.max(0, (performance.now() - state.lastVisualTickTime) / tickMs));
}

export function resizeCanvas(canvas, ctx) {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width  = Math.floor(rect.width  * ratio);
  canvas.height = Math.floor(rect.height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

// ── Particles ────────────────────────────────────────────────────────────────

function emitParticles(state, screenX, screenY, color, dirX, now) {
  for (let i = 0; i < 2; i++) {
    state.particles.push({
      x:     screenX - dirX * (Math.random() * 3 + 1),
      y:     screenY + (Math.random() - 0.5) * 6,
      vx:    -dirX * (Math.random() * 0.6 + 0.2),
      vy:    (Math.random() - 0.5) * 0.5,
      born:  now,
      life:  400 + Math.random() * 200,
      color,
    });
  }
  if (state.particles.length > 40) {
    state.particles.splice(0, state.particles.length - 40);
  }
}

function updateAndDrawParticles(ctx, state, now) {
  state.particles = state.particles.filter((p) => now - p.born < p.life);
  for (const p of state.particles) {
    const t = (now - p.born) / p.life;
    p.x += p.vx;
    p.y += p.vy;
    ctx.save();
    ctx.globalAlpha = (1 - t) * 0.85;
    ctx.shadowBlur  = 6;
    ctx.shadowColor = p.color;
    ctx.fillStyle   = p.color;
    ctx.beginPath();
    ctx.arc(p.x, p.y, (1 - t) * 2.5 + 0.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

// ── Platform ─────────────────────────────────────────────────────────────────

function drawPlatform(ctx, entity, camera, viewHeight, now) {
  const { width, height } = entity.Collision;
  const center  = worldToScreen(camera, unfixed(entity.Position.x), unfixed(entity.Position.y), viewHeight);
  const screenW = unfixed(width)  * TILE_SIZE;
  const screenH = unfixed(height) * TILE_SIZE;
  const x = center.x - screenW / 2;
  const y = center.y - screenH / 2;

  if (entity.Trigger) {
    ctx.save();
    ctx.fillStyle   = 'rgba(0,255,224,0.07)';
    ctx.strokeStyle = 'rgba(0,255,224,0.4)';
    ctx.setLineDash([6, 4]);
    ctx.fillRect(x, y, screenW, screenH);
    ctx.strokeRect(x, y, screenW, screenH);
    ctx.setLineDash([]);
    ctx.restore();
    return;
  }

  const elevated = entity.Position.y > 4200;
  const colorA   = elevated ? MAGENTA : CYAN;
  const colorB   = elevated ? PURPLE  : BLUE;

  ctx.save();

  // base gradient + glow
  ctx.shadowBlur  = 14;
  ctx.shadowColor = colorA;
  const grad = ctx.createLinearGradient(x, 0, x + screenW, 0);
  grad.addColorStop(0,   colorB);
  grad.addColorStop(0.5, colorA);
  grad.addColorStop(1,   colorB);
  ctx.fillStyle = grad;
  ctx.fillRect(x, y, screenW, screenH);

  // shimmer highlight sweeps left→right every 3 s
  ctx.shadowBlur = 0;
  const shimmerCX = x + ((now % 3000) / 3000) * (screenW + 80) - 40;
  const shimmer   = ctx.createLinearGradient(shimmerCX - 20, 0, shimmerCX + 20, 0);
  shimmer.addColorStop(0,   'rgba(255,255,255,0)');
  shimmer.addColorStop(0.5, 'rgba(255,255,255,0.3)');
  shimmer.addColorStop(1,   'rgba(255,255,255,0)');
  ctx.fillStyle = shimmer;
  ctx.fillRect(x, y, screenW, screenH);

  // top edge highlight
  ctx.fillStyle = 'rgba(255,255,255,0.45)';
  ctx.fillRect(x, y, screenW, 1);

  ctx.restore();
}

// ── Unit ─────────────────────────────────────────────────────────────────────

function drawUnit(ctx, state, screenX, screenY, mine, direction, collision, now) {
  const screenW = Math.max(MIN_UNIT_W, unfixed(collision.width)  * TILE_SIZE);
  const screenH = Math.max(MIN_UNIT_H, unfixed(collision.height) * TILE_SIZE);
  const x = screenX - screenW / 2;
  const y = screenY - screenH / 2;

  const colorA = mine ? CYAN    : MAGENTA;
  const colorB = mine ? BLUE    : PURPLE;
  const pulse  = 14 + 8 * Math.sin(now / 900);

  ctx.save();
  ctx.shadowBlur  = pulse;
  ctx.shadowColor = colorA;
  const grad = ctx.createLinearGradient(x, y, x, y + screenH);
  grad.addColorStop(0, colorA);
  grad.addColorStop(1, colorB);
  ctx.fillStyle = grad;
  ctx.fillRect(x, y, screenW, screenH);
  ctx.restore();

  if (direction.x !== 0) {
    emitParticles(state, screenX, screenY, colorA, direction.x, now);
  }
}

// ── Scan line sweep ───────────────────────────────────────────────────────────

function drawScanLine(ctx, rect, now) {
  const y    = ((now % 4000) / 4000) * rect.height;
  const grad = ctx.createLinearGradient(0, y - 3, 0, y + 3);
  grad.addColorStop(0,   'rgba(0,255,224,0)');
  grad.addColorStop(0.5, 'rgba(0,255,224,0.18)');
  grad.addColorStop(1,   'rgba(0,255,224,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, y - 3, rect.width, 6);
}

// ── Frame ─────────────────────────────────────────────────────────────────────

export function renderFrame(ctx, canvas, state) {
  const now  = performance.now();
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  drawMap(ctx, state.camera, rect);

  for (const entity of collidables(state.snapshot)) {
    if ('OwnedBy' in entity) continue;
    drawPlatform(ctx, entity, state.camera, rect.height, now);
  }

  const alpha  = visualAlpha(state);
  const issuer = state.playerId;

  for (const entity of units(state.snapshot)) {
    const position  = unitVisualPosition(entity, alpha);
    const direction = unitDirection(entity);
    const screenPos = worldToScreen(state.camera, unfixed(position.x), unfixed(position.y), rect.height);
    const mine      = entity.OwnedBy.owner === issuer;

    drawUnit(ctx, state, screenPos.x, screenPos.y, mine, direction, entity.Collision, now);

    if (state.selectedUnit === entity.id) {
      const selW = Math.max(MIN_UNIT_W, unfixed(entity.Collision.width)  * TILE_SIZE);
      const selH = Math.max(MIN_UNIT_H, unfixed(entity.Collision.height) * TILE_SIZE);
      ctx.save();
      ctx.strokeStyle = 'rgba(255,255,255,0.7)';
      ctx.lineWidth   = 1;
      ctx.setLineDash([3, 3]);
      ctx.strokeRect(screenPos.x - selW / 2 - 3, screenPos.y - selH / 2 - 3, selW + 6, selH + 6);
      ctx.restore();
    }
  }

  updateAndDrawParticles(ctx, state, now);
  drawScanLine(ctx, rect, now);
}
