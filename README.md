# Python Game Architecture

Deterministic lockstep architecture.

The server runs one authoritative game world. Clients receive snapshots and
command frames, then run the same fixed-tick simulation locally for prediction
and checksum validation.

## Goals

- Low network overhead through semantic commands.
- Deterministic simulation with replay support.
- Predictable latency through fixed command delay.

## Architecture

- `core`: deterministic command model, binary protocol helpers, checksums.
- `game`: single esper world, components, movement processor, simulation step.
- [esper](https://github.com/benmoran56/esper): ECS library.
- `server`: websocket server and match coordinator over the shared world.
- `config`: match and initial spawn configuration.
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

Run a server (tokens are pre-shared secrets issued to each client by the launcher):

```bash
server --host 127.0.0.1 --port 8766 --player-tokens alice-token bob-token
```

Omit `--player-tokens` to connections become spectators and cannot issue commands.

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

### Auth handshake

Every connection must send an auth message as its **first frame** before any
other message is accepted. The server closes the connection silently on an
unknown token or a 10-second timeout.

```python
# client → server (first message)
{"kind": "auth", "token": "<pre-shared-token>"}

# server → client (on success)
{"kind": "state_sync", "player_id": 6, "snapshot": ..., "command_frames": [...], ...}
```

`player_id` is the server-assigned entity ID that owns the client's units.

### Commands

Command frames contain intentions, not replicated unit state. The server
assigns the `issuer` from the authenticated connection — the wire field is
ignored.

```python
# client → server
{"kind": "command", "command": {"type": "MOVE", "sequence": 1, "targets": [7, 8], "x": 1}}

# server → client
{"kind": "command_accepted", "sequence": 1, "assigned_tick": 105}

# server → all clients (each tick)
{"kind": "command_frame", "tick": 105, "commands": [...]}
```

### Checksums

Clients periodically send deterministic state checksums. The server validates
only ticks within the window `[snapshot_tick, current_tick + checksum_interval]`.

```python
# client → server
{"kind": "checksum", "tick": 200, "checksum": "7d87f1ab"}
```

Server compares client checksums for the same tick against its own
authoritative value and other clients. If values differ, it broadcasts a
`desync_report` with checksum groups by participant.

## Known Issues:

- [ ] No backpressure for broadcast
- [ ] No Rate-Limit on commands