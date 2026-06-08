# RTS Engine 2

Pure Python prototype for a deterministic lockstep RTS architecture.

The server coordinates the authoritative command timeline, but it does not own
or replicate full world state. Clients start from the same initial state,
receive the same command frames, and run the same fixed-tick simulation locally.

## Goals

- 2-16 player matches.
- Hundreds or thousands of units per match.
- Low network overhead through semantic commands.
- Deterministic simulation with replay support.
- Predictable latency through fixed command delay.

## Non-goals

- MMO scale.
- Persistent worlds.
- Server-authoritative physics.
- Full state replication.

## Architecture

- `core`: deterministic command model, binary protocol helpers, checksums.
- `game`: RTS world, components, esper processors, and simulation loop.
- [esper](https://github.com/benmoran56/esper): third-party ECS library (entities, components, processors).
- `server`: asyncio websocket coordinator and match timeline.
- `config`: shared server/simulation/bootstrap configuration.
- `web/index.html` and `web/client/`: browser canvas demo client.

## Determinism Rules

- Simulation uses integer coordinates and velocities.
- Every tick applies commands in canonical `(tick, player_id, sequence, command)` order.
- Entity iteration is sorted by stable unit id.
- Networking never mutates simulation state directly.
- Async is allowed around I/O, not inside the simulation update.

## Quick Start

Install for development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Run a coordinator:

```bash
server --host 127.0.0.1 --port 8765
```

Run the browser demo:

```bash
server --host 127.0.0.1 --port 8765 --tick-rate 20 --command-delay-ticks 2
python -m http.server 8080 -d web
```

Then open `http://127.0.0.1:8080`, connect to `ws://127.0.0.1:8765`,
left-click one of your units, and right-click to issue a move command through
the lockstep server.

Run a 100-bot load test and play as `p101` in the browser:

```bash
server --host 127.0.0.1 --port 8765 --tick-rate 20 --command-delay-ticks 2
python scripts/bot_swarm.py --url ws://127.0.0.1:8765 --first-player 1 --count 100 --command-interval 1.0
python -m http.server 8080 -d web
```

Then open `http://127.0.0.1:8080`, keep player `p101`, and connect. Each bot
owns one unit and sends periodic `MOVE` commands through the same server
timeline.

## State Sync

New clients receive a `state_sync` message:

- `snapshot`: deterministic world snapshot at `snapshot_tick`.
- `command_frames`: authoritative command history after the snapshot.
- `current_tick`: tick to replay up to before live frames continue.

The server keeps this snapshot as a bootstrap cache. Late-joining clients
reconstruct state by loading the latest snapshot and replaying only the command
tail after it.

## Protocol

Runtime transport uses websocket frames carrying MessagePack payloads.
Command frames contain intentions, not replicated unit state:

```python
{
    "kind": "command_frame",
    "tick": 103,
    "commands": [
        {"type": "MOVE", "player_id": "p1", "units": [1, 2, 3], "x": 100, "y": 200}
    ],
}
```

Clients periodically send deterministic state checksums:

```python
{"kind": "checksum", "player_id": "p1", "tick": 200, "checksum": "7d87f1ab"}
```

The coordinator compares client checksums for the same tick against its
deterministic bootstrap cache and other clients. If values differ, it broadcasts
a `desync_report` with checksum groups by participant.

## Current Scope

This is a foundation, not a finished game. It includes lockstep movement,
state checksums, replay, and a coordinator server. Hot-path systems such as
hierarchical pathfinding, flow fields, and collision avoidance are represented
by deterministic extension points and can be filled in without changing the
lockstep model.
