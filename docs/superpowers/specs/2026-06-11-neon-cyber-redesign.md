# Neon Cyber Visual Redesign

## Summary

Complete visual redesign of the RTS Lockstep client. Direction: **Neon Cyber** — dark background, neon cyan/magenta glows, Orbitron font, six animations.

---

## 1. Design Tokens

```
Background:   #07080f
Surface:      #0d0f1a
Cyan:         #00ffe0   (P1, UI accent)
Blue:         #006eff   (P1 secondary, platforms)
Magenta:      #ff00c8   (P2)
Purple:       #a000ff   (P2 secondary, mid-platforms)
Border:       rgba(0,255,224,.15)
Font:         'Orbitron', sans-serif  — Google Fonts
```

---

## 2. UI (index.html + ui.js)

**Header** — dark bar with bottom neon gradient line:
- Brand `CYBER` in white with cyan text-shadow glow
- Inputs/selects styled: dark bg, cyan border, Orbitron font
- Buttons: `CONNECT` with blue glow, `RESET`/`RESYNC` muted
- Status: dot + text (dot pulses via CSS animation)
- Pills (UNIT, TPS) right-aligned, neon border

**Sidebar panels** — dark cards with cyan border:
- Panel headers: uppercase, letter-spaced, dim cyan
- Stat rows: label dim / value bright, separated by faint lines
- Controls text: dim with bright key highlights

**Status transitions (animation 5):** when `setStatus()` is called, the element fades out and fades+blurs in. Implemented via CSS class toggle + transition.

---

## 3. Canvas Rendering (render.js)

The canvas renders at 60fps via `requestAnimationFrame`. All canvas animations are driven by `performance.now()` passed into the render function.

**Background:**
- Fill `#07080f`
- Faint grid: lines every 60 world-units, `rgba(0,255,224,.025)` — drawn in world space, follows camera

**Platforms (no Trigger component):**
- Fill: gradient cyan→blue (floor) or magenta→purple (elevated)
- Glow: `ctx.shadowBlur = 18`, `ctx.shadowColor = #00ffe0`
- Shimmer (animation 2): a bright highlight sweeps left→right over ~3 seconds. Implemented as a moving linear gradient clipped to the platform rect — offset = `(time % 3000) / 3000 * (width + 200) - 100`
- Top edge: 1px brighter line for depth

**Players:**
- Fill: gradient P1 cyan→blue, P2 magenta→purple
- Glow: `shadowBlur = 20`, color matches player
- Glow pulse (animation 1): `shadowBlur` oscillates between 12 and 28 using `sin(time / 900)`
- Player label (`P1`/`P2`) above unit in matching color, Orbitron 9px
- Uses `unitVisualPosition(entity, alpha)` for interpolated position

**Particle trail (animation 4):**
- When `movement.x !== 0`, emit 1 particle per frame at player's trailing edge
- Each particle: 3–5px circle, player color, velocity `(-movement.x * 0.3 + rand, rand * 0.5)` in screen coords, lifetime 500ms, fade out linearly
- Max 40 particles in pool to cap memory. Stored in `state.particles[]`

**Scan line sweep (animation 3):**
- After all game objects drawn: a 2px horizontal line in `rgba(0,255,224,.25)` sweeps from top to bottom every 4 seconds
- Drawn in screen space (ignore camera transform)
- Subtle scanline texture: `repeating-linear-gradient` pattern at 10% opacity via a CSS overlay div on top of canvas (not drawn in canvas)

**Alpha interpolation (animation 6):**
- `render.js` receives `alpha = timeSinceLastTick / msPerTick` (clamped 0–1)
- Calls `unitVisualPosition(entity, alpha)` — already implemented in `simulation.js`
- `alpha` computed in `draw()` as `clamp((now - state.lastVisualTickTime) / (1000 / state.tickRate), 0, 1)`

---

## 4. Animations Summary

| # | Name | Where | Complexity |
|---|------|--------|-----------|
| 1 | Glow pulse on players | canvas render | easy |
| 2 | Platform shimmer | canvas render | easy |
| 3 | Scan line sweep | CSS overlay | easy |
| 4 | Particle trail | canvas + state | medium |
| 5 | Status/HUD transitions | CSS + ui.js | easy |
| 6 | Alpha interpolation | app.js + render.js | easy (partial) |

---

## 5. Files Changed

| File | Change |
|------|--------|
| `web/index.html` | Full restyle — CSS vars, Orbitron import, all elements |
| `web/client/render.js` | Neon rendering, shimmer, glow pulse, particles, scan line, alpha |
| `web/client/app.js` | Compute + pass `alpha` to render; init `state.particles` |
| `web/client/ui.js` | Status transition animation on `setStatus` |

---

## 6. Out of Scope

- No changes to game logic, server, or collision code
- No sound effects
- No animated sprites / character art — players remain rectangles
