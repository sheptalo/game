from __future__ import annotations

import argparse
import asyncio
import contextlib
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

import websockets

from config import MatchConfig
from game.protocol import command_from_client_wire
from server.match import MatchCoordinator
from server.protocol import pack_message, unpack_message


@dataclass(slots=True)
class LockstepServer:
    coordinator: MatchCoordinator = field(default_factory=MatchCoordinator)
    clients: set[Any] = field(default_factory=set)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    async def handler(self, websocket: Any) -> None:
        self.clients.add(websocket)
        await websocket.send(pack_message(self.coordinator.state_sync_payload()))
        try:
            async for payload in websocket:
                message = unpack_message(payload)
                if message.get("kind") == "state_sync_request":
                    await websocket.send(
                        pack_message(self.coordinator.state_sync_payload())
                    )
                    continue

                if message.get("kind") == "checksum":
                    report = self.coordinator.record_checksum(
                        player_id=str(message["player_id"]),
                        tick=int(message["tick"]),
                        checksum=str(message["checksum"]),
                    )
                    if report is not None:
                        await self.broadcast(report)
                    continue

                if message.get("kind") != "command":
                    continue

                command = command_from_client_wire(message["command"])
                assigned_tick = self.coordinator.assign_command(command)
                await websocket.send(
                    pack_message(
                        {
                            "kind": "command_accepted",
                            "sequence": command.sequence,
                            "assigned_tick": int(assigned_tick),
                        }
                    )
                )
        finally:
            self.clients.discard(websocket)

    async def run_ticks(self) -> None:
        duration = 1.0 / self.coordinator.config.tick_rate
        delay = 0
        while True:
            await asyncio.sleep(duration - delay)
            start = monotonic()
            frame = self.coordinator.build_frame()
            await self.broadcast(frame.to_wire())
            delay = max(monotonic() - start, 0)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self.clients:
            return
        payload = pack_message(message)
        _ = asyncio.create_task(self.background_broadcast(payload))

    async def background_broadcast(self, payload: bytes) -> None:
        disconnected: list[Any] = []
        for client in tuple(self.clients):
            try:
                await client.send(payload)
            except Exception:
                disconnected.append(client)
        for client in disconnected:
            self.clients.discard(client)


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
