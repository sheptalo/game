"""Three-phase load test for the lockstep RTS server."""
from __future__ import annotations

import asyncio
import random
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import msgpack
import websockets


ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"


def pack(msg: dict) -> bytes:
    return msgpack.packb(msg, use_bin_type=True, strict_types=True)


def unpack(data: bytes) -> dict:
    return msgpack.unpackb(data, raw=False, strict_map_key=False)


@dataclass
class ClientResult:
    frame_intervals_ms: list[float] = field(default_factory=list)
    frames_received: int = 0
    errored: bool = False
    disconnected_early: bool = False


@dataclass
class PhaseConfig:
    name: str
    n_tokens: int          # total player slots on the server
    n_connections: int     # WebSocket connections to open
    n_active: int          # connections that send MOVE/JUMP commands
    n_slow: int            # connections that sleep 2 s between recv calls
    tick_rate: int
    duration_s: float
    move_every_range: tuple[int, int]   # (min, max) ticks between MOVE sends
    jump_every_range: tuple[int, int]   # (min, max) ticks between JUMP sends
    port: int


def make_tokens(n: int) -> list[str]:
    return [secrets.token_hex(8) for _ in range(n)]


def start_server(tokens: list[str], port: int, tick_rate: int) -> subprocess.Popen:
    env = {"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    cmd = [
        sys.executable, "-m", "server",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--tick-rate", str(tick_rate),
        "--player-tokens", *tokens,
    ]
    return subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def sample_rss_kb(pid: int) -> int:
    """Read RSS in KB via `ps`. Works on macOS and Linux."""
    try:
        out = subprocess.check_output(
            ["ps", "-o", "rss=", "-p", str(pid)],
            stderr=subprocess.DEVNULL,
        )
        return int(out.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return 0


async def poll_rss(pid: int, stop: asyncio.Event) -> list[int]:
    """Sample server RSS every second until stop is set. Returns KB samples."""
    samples: list[int] = []
    while not stop.is_set():
        samples.append(sample_rss_kb(pid))
        await asyncio.sleep(1.0)
    return samples


def find_unit_id(snapshot: dict, player_id: int) -> int | None:
    """Return the entity id of the unit owned by player_id, or None."""
    for entity in snapshot.get("entities", []):
        owned = entity.get("OwnedBy")
        if owned and owned.get("owner") == player_id:
            return entity["id"]
    return None


async def run_client(
    token: str,
    url: str,
    deadline: float,          # asyncio.get_event_loop().time() deadline
    slow: bool = False,
    active: bool = False,
    move_every: int = 3,
    jump_every: int = 20,
) -> ClientResult:
    result = ClientResult()
    try:
        async with websockets.connect(
            url,
            compression=None,
            ping_interval=None,
            open_timeout=5.0,
        ) as ws:
            # Auth handshake
            await ws.send(pack({"kind": "auth", "token": token}))

            # Wait for state_sync
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            msg = unpack(raw)
            if msg.get("kind") != "state_sync":
                result.errored = True
                return result

            player_id: int | None = msg.get("player_id")
            snapshot = msg.get("snapshot", {})
            unit_id: int | None = find_unit_id(snapshot, player_id) if player_id is not None else None
            seq = 1
            local_tick = 0
            last_frame_time: float | None = None
            loop = asyncio.get_event_loop()

            while loop.time() < deadline:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 2.0))
                except asyncio.TimeoutError:
                    break

                if slow:
                    await asyncio.sleep(2.0)

                now = loop.time() * 1000  # ms
                if last_frame_time is not None:
                    result.frame_intervals_ms.append(now - last_frame_time)
                last_frame_time = now

                msg = unpack(raw)
                if msg.get("kind") != "command_frame":
                    continue

                result.frames_received += 1
                local_tick += 1

                if active and unit_id is not None:
                    if local_tick % move_every == 0:
                        direction = random.choice([-1, 1])
                        await ws.send(pack({
                            "kind": "command",
                            "command": {
                                "type": "MOVE",
                                "sequence": seq,
                                "targets": [unit_id],
                                "x": direction,
                            },
                        }))
                        seq += 1
                    if local_tick % jump_every == 0:
                        await ws.send(pack({
                            "kind": "command",
                            "command": {
                                "type": "JUMP",
                                "sequence": seq,
                                "targets": [unit_id],
                            },
                        }))
                        seq += 1

    except (OSError, websockets.exceptions.WebSocketException, asyncio.TimeoutError) as exc:
        result.errored = True
        _ = exc
    return result


@dataclass
class PhaseResult:
    phase: PhaseConfig
    client_results: list[ClientResult]
    rss_samples_kb: list[int]
    duration_s: float


async def run_phase(cfg: PhaseConfig) -> PhaseResult:
    tokens = make_tokens(cfg.n_tokens)
    url = f"ws://127.0.0.1:{cfg.port}"

    proc = start_server(tokens, cfg.port, cfg.tick_rate)
    await asyncio.sleep(0.8)  # wait for server to bind

    loop = asyncio.get_event_loop()
    deadline = loop.time() + cfg.duration_s

    # Assign roles to connection indices:
    # [0 .. n_active-1]               → active, non-slow
    # [n_active .. n_active+n_slow-1] → passive, slow
    # rest                            → passive, non-slow
    coroutines = []
    for i in range(cfg.n_connections):
        is_active = i < cfg.n_active
        is_slow = cfg.n_active <= i < cfg.n_active + cfg.n_slow
        if is_active:
            move_every = random.randint(*cfg.move_every_range)
            jump_every = random.randint(*cfg.jump_every_range)
        else:
            move_every = 1
            jump_every = 1
        coroutines.append(run_client(
            token=tokens[i],
            url=url,
            deadline=deadline,
            slow=is_slow,
            active=is_active,
            move_every=move_every,
            jump_every=jump_every,
        ))

    stop_rss = asyncio.Event()
    rss_task = asyncio.create_task(poll_rss(proc.pid, stop_rss))

    t0 = time.monotonic()
    results: list[ClientResult] = list(await asyncio.gather(*coroutines, return_exceptions=False))
    elapsed = time.monotonic() - t0

    stop_rss.set()
    rss_samples = await rss_task

    proc.terminate()
    proc.wait()

    return PhaseResult(
        phase=cfg,
        client_results=results,
        rss_samples_kb=rss_samples,
        duration_s=elapsed,
    )
