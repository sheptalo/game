"""Three-phase load test for the lockstep RTS server."""
from __future__ import annotations

import asyncio
import os
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

    def __post_init__(self) -> None:
        if self.n_connections > self.n_tokens:
            raise ValueError(
                f"n_connections ({self.n_connections}) must be <= n_tokens ({self.n_tokens})"
            )
        if self.n_active + self.n_slow > self.n_connections:
            raise ValueError(
                f"n_active + n_slow ({self.n_active + self.n_slow}) must be <= n_connections ({self.n_connections})"
            )


def make_tokens(n: int) -> list[str]:
    return [secrets.token_hex(8) for _ in range(n)]


def start_server(tokens: list[str], port: int, tick_rate: int) -> subprocess.Popen:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
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
            loop = asyncio.get_running_loop()

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

                msg = unpack(raw)
                if msg.get("kind") != "command_frame":
                    continue

                now = loop.time() * 1000  # ms
                if last_frame_time is not None:
                    result.frame_intervals_ms.append(now - last_frame_time)
                last_frame_time = now

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

    except (OSError, websockets.exceptions.WebSocketException, asyncio.TimeoutError):
        if result.frames_received > 0:
            result.disconnected_early = True
        else:
            result.errored = True
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

    loop = asyncio.get_running_loop()
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
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    return PhaseResult(
        phase=cfg,
        client_results=results,
        rss_samples_kb=rss_samples,
        duration_s=elapsed,
    )


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)


TARGET_INTERVAL_MS = 1000 / 60  # ~16.67 ms at 60 Hz


def print_phase_report(result: PhaseResult) -> None:
    cfg = result.phase
    clients = result.client_results
    n = len(clients)
    errored = sum(1 for c in clients if c.errored)
    disc_early = sum(1 for c in clients if c.disconnected_early)
    surviving = n - errored - disc_early

    normal_intervals: list[float] = []
    for i, c in enumerate(clients):
        is_slow = cfg.n_active <= i < cfg.n_active + cfg.n_slow
        if not is_slow and not c.errored:
            normal_intervals.extend(c.frame_intervals_ms)

    p50 = percentile(normal_intervals, 50)
    p95 = percentile(normal_intervals, 95)
    p99 = percentile(normal_intervals, 99)
    peak_rss_mb = max(result.rss_samples_kb, default=0) / 1024

    expected_frames = int(cfg.tick_rate * cfg.duration_s)
    total_received = sum(c.frames_received for c in clients if not c.errored)

    print(f"\n{'='*60}")
    print(f"Phase: {cfg.name}")
    print(f"  Connections:       {surviving} / {n} survived")
    print(f"  Errors:            {errored}")
    print(f"  Disconnected early: {disc_early}")
    print(f"  Frames received:   {total_received}  (expected ~{expected_frames * surviving})")
    print(f"  Inter-frame P50:   {p50:.1f} ms  (target {TARGET_INTERVAL_MS:.1f} ms)")
    print(f"  Inter-frame P95:   {p95:.1f} ms")
    print(f"  Inter-frame P99:   {p99:.1f} ms")
    if result.rss_samples_kb:
        print(f"  Server peak RSS:   {peak_rss_mb:.1f} MB")

    if p99 > TARGET_INTERVAL_MS * 2 or errored > n * 0.05 or disc_early > n * 0.05:
        print("  ⚠  BOTTLENECK DETECTED")


async def main() -> None:
    phases = [
        PhaseConfig(
            name="Phase 1 — Baseline (16 clients, 15 s)",
            n_tokens=16,
            n_connections=16,
            n_active=16,
            n_slow=0,
            tick_rate=60,
            duration_s=15.0,
            move_every_range=(3, 3),
            jump_every_range=(10, 10),
            port=8801,
        ),
        PhaseConfig(
            name="Phase 2 — Slow stress (200 clients, 30 s)",
            n_tokens=200,
            n_connections=200,
            n_active=2,
            n_slow=40,
            tick_rate=60,
            duration_s=30.0,
            move_every_range=(3, 3),
            jump_every_range=(10, 10),
            port=8802,
        ),
        PhaseConfig(
            name="Phase 3 — Super stress (200 clients / 50 active, 30 s)",
            n_tokens=200,
            n_connections=200,
            n_active=50,
            n_slow=0,
            tick_rate=60,
            duration_s=30.0,
            move_every_range=(2, 5),
            jump_every_range=(15, 30),
            port=8803,
        ),
    ]

    print("Starting load test — 3 phases")
    print(f"Server binary: {sys.executable} -m server")

    for cfg in phases:
        print(f"\nRunning {cfg.name} ...")
        result = await run_phase(cfg)
        print_phase_report(result)
        await asyncio.sleep(2.0)

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
