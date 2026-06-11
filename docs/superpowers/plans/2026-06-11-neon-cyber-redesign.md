# Neon Cyber Visual Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current placeholder visuals with a Neon Cyber aesthetic — dark background, neon cyan/magenta glows, Orbitron font, six animations (glow pulse, shimmer, scan line, particles, status transition, alpha interpolation).

**Architecture:** Pure client-side visual layer — no simulation logic changes. Game state gains a `particles` array. Map background replaces terrain tiles with a dark grid. Render pipeline gains time-based effects driven by `performance.now()`.

**Tech Stack:** Vanilla JS ES modules, Canvas 2D API, CSS custom properties, Google Fonts (Orbitron).

---

## File Map

| File | Change |
|------|--------|
| `web/client/simulation.js` | Add `particles: []` to `createGameState()` |
| `web/client/ui.js` | Clear particles in `resetLocalWorld`; animate `setStatus` |
| `web/client/map.js` | Replace terrain `drawMap` with dark bg + faint world-space grid |
| `web/client/render.js` | Full neon rewrite — platform shimmer, unit glow pulse, particle trail, scan line |
| `web/index.html` | Orbitron import, CSS custom properties, full restyle, brand "CYBER" |

---

## Task 1: Add particles array to game state

**Files:**
- Modify: `web/client/simulation.js` (function `createGameState`)

- [ ] **Add `particles: []` to createGameState**

  In `createGameState()`, add the field after `triggerEvents`:

  ```js
  // web/client/simulation.js — createGameState(), last field:
    triggerEvents: [],
    particles: [],
  ```

- [ ] **Commit**

  ```bash
  git add web/client/simulation.js
  git commit -m "feat: add particles array to game state"
  ```

---

## Task 2: Dark neon background

**Files:**
- Modify: `web/client/map.js` (function `drawMap` only — keep `worldToScreen`, `clampCamera`)

- [ ] **Replace drawMap with dark background + faint world-space grid**

  Replace the entire `drawMap` function body (keep the export):

  ```js
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
  ```

- [ ] **Commit**

  ```bash
  git add web/client/map.js
  git commit -m "feat: replace terrain map with neon dark background"
  ```

---

## Task 3: Neon canvas rendering

**Files:**
- Modify: `web/client/render.js` (full rewrite)

- [ ] **Write new render.js**

  ```js
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
    const issuer = resolveIssuer(state.snapshot, state.currentPlayer);

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
  ```

- [ ] **Commit**

  ```bash
  git add web/client/render.js
  git commit -m "feat: neon cyber canvas rendering with particles and animations"
  ```

---

## Task 4: UI restyle (index.html)

**Files:**
- Modify: `web/index.html` (full rewrite of `<style>` block and `<header>`/`<aside>` markup)

- [ ] **Write new index.html**

  ```html
  <!doctype html>
  <html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CYBER</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
      *, *::before, *::after { box-sizing: border-box; }

      :root {
        --cyan:    #00ffe0;
        --blue:    #006eff;
        --magenta: #ff00c8;
        --purple:  #a000ff;
        --bg:      #07080f;
        --surface: #0d0f1a;
        --border:  rgba(0,255,224,.15);
        --font:    'Orbitron', sans-serif;
        color-scheme: dark;
      }

      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        grid-template-rows: 44px 1fr;
        font-family: var(--font);
        background: var(--bg);
        color: var(--cyan);
      }

      /* ── HEADER ── */
      header {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        padding: 0 14px;
        background: rgba(0,0,0,.85);
        border-bottom: 1px solid var(--border);
        box-shadow: 0 0 24px rgba(0,255,224,.05);
        position: relative;
      }
      header::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, var(--cyan) 30%, var(--blue) 70%, transparent);
        opacity: .35;
      }

      .brand {
        font-size: 13px;
        font-weight: 900;
        letter-spacing: .25em;
        color: #fff;
        text-shadow: 0 0 12px var(--cyan), 0 0 32px rgba(0,255,224,.3);
        margin-right: 4px;
      }

      label {
        display: flex;
        gap: 6px;
        align-items: center;
        font-size: 8px;
        letter-spacing: .12em;
        color: rgba(0,255,224,.45);
      }

      input, button, select {
        font-family: var(--font);
        font-size: 8px;
        letter-spacing: .06em;
        background: rgba(0,255,224,.04);
        border: 1px solid rgba(0,255,224,.2);
        border-radius: 4px;
        padding: 5px 8px;
        color: var(--cyan);
        outline: none;
      }

      button {
        cursor: pointer;
        font-weight: 700;
        letter-spacing: .12em;
        transition: box-shadow .15s ease, background .15s ease;
      }
      button:hover { filter: brightness(1.15); }

      button.primary {
        background: rgba(0,110,255,.18);
        border-color: rgba(0,110,255,.45);
        box-shadow: 0 0 10px rgba(0,110,255,.2);
      }
      button.primary:hover {
        box-shadow: 0 0 18px rgba(0,110,255,.55);
      }

      button.secondary {
        background: rgba(255,255,255,.04);
        border-color: rgba(255,255,255,.1);
        color: rgba(255,255,255,.35);
      }

      /* ── STATUS ── */
      @keyframes status-appear {
        from { opacity: 0; transform: translateY(-3px); filter: blur(3px); }
        to   { opacity: 1; transform: translateY(0);    filter: blur(0);   }
      }
      .status-appear { animation: status-appear .25s ease-out forwards; }

      .ok   { color: var(--cyan);    text-shadow: 0 0 8px var(--cyan); }
      .warn { color: #ffcc00;        text-shadow: 0 0 8px #ffcc00; }
      .bad  { color: #ff4466;        text-shadow: 0 0 8px #ff4466; }

      #status {
        font-size: 8px;
        letter-spacing: .14em;
        font-weight: 700;
      }

      /* ── PILLS ── */
      .hud-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 10px;
        border: 1px solid var(--border);
        border-radius: 999px;
        font-size: 8px;
        letter-spacing: .08em;
        background: rgba(0,0,0,.4);
        color: rgba(0,255,224,.5);
      }
      .hud-pill strong {
        color: var(--cyan);
        font-weight: 700;
      }

      /* ── LAYOUT ── */
      main {
        display: grid;
        grid-template-columns: 1fr 280px;
        min-height: 0;
      }

      canvas {
        width: 100%;
        height: 100%;
        display: block;
        background: var(--bg);
      }

      /* ── SIDEBAR ── */
      aside {
        padding: 14px;
        border-left: 1px solid var(--border);
        background: var(--surface);
        overflow: auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .panel {
        border: 1px solid var(--border);
        border-radius: 8px;
        background: rgba(0,0,0,.4);
        overflow: hidden;
      }

      .panel-header {
        padding: 7px 12px;
        font-size: 8px;
        letter-spacing: .2em;
        color: rgba(0,255,224,.4);
        border-bottom: 1px solid var(--border);
        background: rgba(0,255,224,.02);
      }

      .panel-body { padding: 12px; }

      .stat {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        padding: 5px 0;
        border-bottom: 1px solid rgba(0,255,224,.06);
        font-size: 8px;
        letter-spacing: .08em;
      }
      .stat:last-child { border-bottom: none; }
      .stat span  { color: rgba(0,255,224,.4); }
      .stat strong {
        color: var(--cyan);
        font-variant-numeric: tabular-nums;
        font-weight: 700;
      }
      .stat strong.blue { color: var(--blue); }

      .hint {
        font-size: 8px;
        letter-spacing: .06em;
        line-height: 1.85;
        color: rgba(0,255,224,.35);
      }
      .hint b {
        color: rgba(0,255,224,.75);
        font-weight: 700;
      }
    </style>
  </head>
  <body>
    <header>
      <div class="brand">CYBER</div>
      <label>SERVER <input id="url" size="24" value="ws://127.0.0.1:8766"></label>
      <label>PLAYER
        <select id="player">
          <option value="p1">P1</option>
          <option value="p2">P2</option>
        </select>
      </label>
      <button id="connect" class="primary">CONNECT</button>
      <button id="reset" class="secondary">RESET</button>
      <button id="resync" class="secondary">RESYNC</button>
      <span id="status" class="warn">OFFLINE</span>
      <div style="margin-left:auto;display:flex;gap:8px">
        <span class="hud-pill">UNIT <strong id="selected">—</strong></span>
        <span class="hud-pill">TPS <strong id="tps">—</strong></span>
      </div>
    </header>

    <main>
      <canvas id="game"></canvas>
      <aside>
        <div class="panel">
          <div class="panel-header">CONTROLS</div>
          <div class="panel-body">
            <div class="hint">
              <b>A / D</b> — move left / right<br>
              <b>W</b> — jump (grounded only)<br>
              <b>SPACE / MMB</b> — pan camera
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">STATS</div>
          <div class="panel-body">
            <div class="stat"><span>TICK</span><strong id="tick">0</strong></div>
            <div class="stat"><span>CHECKSUM</span><strong id="checksum" class="blue">—</strong></div>
            <div class="stat"><span>QUEUED</span><strong id="queued">0</strong></div>
          </div>
        </div>
      </aside>
    </main>

    <script type="module">
      import { createGame } from "./client/app.js";
      createGame();
    </script>
  </body>
  </html>
  ```

- [ ] **Commit**

  ```bash
  git add web/index.html
  git commit -m "feat: neon cyber UI restyle with Orbitron font"
  ```

---

## Task 5: Status transition + particle reset

**Files:**
- Modify: `web/client/ui.js`

- [ ] **Update setStatus and resetLocalWorld**

  Replace `setStatus` (uppercases text to match all-caps UI):

  ```js
  export function setStatus(ui, text, cls) {
    ui.status.textContent = text.toUpperCase();
    ui.status.className = cls;
    ui.status.classList.remove('status-appear');
    void ui.status.offsetWidth; // force reflow so animation restarts
    ui.status.classList.add('status-appear');
  }
  ```

  In `resetLocalWorld`, add particle reset after existing lines:

  ```js
  export function resetLocalWorld(state) {
    state.snapshot = makeSnapshot(state.gameConfig);
    state.simTick = 0;
    state.lastVisualTickTime = performance.now();
    state.selectedUnit = null;
    state.queuedAcks = 0;
    state.frameTimestamps = [];
    state.lastSentDirection = '0,0';
    state.particles = [];          // ADD THIS LINE
    resetTriggerState(state);
    selectDefaultUnit(state);
  }
  ```

  Update `updateUi` so selected unit shows "—" instead of "none":

  ```js
  export function updateUi(ui, state) {
    ui.tick.textContent      = String(state.simTick);
    ui.checksum.textContent  = checksum(state);
    ui.selected.textContent  = state.selectedUnit === null ? '—' : String(state.selectedUnit);
    ui.queued.textContent    = String(state.queuedAcks);
    updateTps(ui, state);
  }
  ```

  Also update `initPlayerOptions` to uppercase the option labels to match the new style (options now read "P1", "P2" — already done in index.html, but this function recreates them dynamically):

  ```js
  export function initPlayerOptions(ui, state) {
    ui.player.replaceChildren();
    for (let playerNumber = 1; playerNumber <= state.gameConfig.player_count; playerNumber += 1) {
      const option = document.createElement('option');
      option.value = `p${playerNumber}`;
      option.textContent = `P${playerNumber}`;
      ui.player.appendChild(option);
    }
    ui.player.value = state.currentPlayer;
  }
  ```

- [ ] **Commit**

  ```bash
  git add web/client/ui.js
  git commit -m "feat: status transition animation and particle reset"
  ```

---

## Verification

After all tasks:

- [ ] Open `web/index.html` in a browser (serve with any static server, e.g. `python3 -m http.server 8080 --directory web`)
- [ ] Verify: dark background, Orbitron font, "CYBER" brand, neon header border
- [ ] Connect to server: status text fades in with blur transition
- [ ] Platforms glow cyan (floor) and magenta (mid), shimmer sweeps across them
- [ ] Units glow cyan (yours) and magenta (other), pulse rhythmically
- [ ] Move a unit: particle trail appears behind it
- [ ] Scan line sweeps top-to-bottom every 4 seconds
