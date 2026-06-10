from __future__ import annotations

import argparse
import asyncio
import contextlib

import websockets

from config import MatchConfig
from server.match import MatchCoordinator
from server.server import LockstepServer


async def serve(
    host: str,
    port: int,
    tick_rate: int,
    command_delay_ticks: int,
    snapshot_interval_ticks: int,
    checksum_interval_ticks: int,
) -> None:
    server = LockstepServer(
        coordinator=MatchCoordinator(
            config=MatchConfig(
                tick_rate=tick_rate,
                command_delay_ticks=command_delay_ticks,
                snapshot_interval_ticks=snapshot_interval_ticks,
                checksum_interval_ticks=checksum_interval_ticks,
            )
        )
    )
    tick_task = asyncio.create_task(server.run_ticks())
    try:
        async with websockets.serve(server.handler, host, port):
            await asyncio.Future()
    finally:
        tick_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tick_task


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RTS lockstep coordinator")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--tick-rate", type=int, default=30)
    parser.add_argument("--command-delay-ticks", type=int, default=2)
    parser.add_argument("--snapshot-interval-ticks", type=int, default=1000)
    parser.add_argument("--checksum-interval-ticks", type=int, default=100)
    args = parser.parse_args()
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(
            serve(
                args.host,
                args.port,
                args.tick_rate,
                args.command_delay_ticks,
                args.snapshot_interval_ticks,
                args.checksum_interval_ticks,
            )
        )


if __name__ == "__main__":
    main()
