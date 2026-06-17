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
