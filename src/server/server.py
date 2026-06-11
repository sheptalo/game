import asyncio
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from websockets import ConnectionClosedError
from websockets.exceptions import ConnectionClosedOK

from game.protocol import command_from_client_wire
from server.match import MatchCoordinator
from server.protocol import pack_message, unpack_message


@dataclass(slots=True)
class LockstepServer:
    coordinator: MatchCoordinator = field(default_factory=MatchCoordinator)
    clients: set[Any] = field(default_factory=set)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    def __post_init__(self) -> None:
        asyncio.create_task(self.background_broadcast())

    async def handler(self, websocket: Any) -> None:
        self.clients.add(websocket)
        await websocket.send(pack_message(self.coordinator.resync_payload()))
        try:
            async for payload in websocket:
                message = unpack_message(payload)
                if message.get("kind") == "state_sync_request":
                    await websocket.send(
                        pack_message(self.coordinator.resync_payload())
                    )
                    continue

                if message.get("kind") == "checksum":
                    report = self.coordinator.record_checksum(
                        player_id=str(message["player_id"]),
                        tick=int(message["tick"]),
                        checksum=str(message["checksum"]),
                    )
                    if report is not None:
                        self.broadcast(report)
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
        except ConnectionClosedError, ConnectionClosedOK:
            pass
        finally:
            self.clients.discard(websocket)

    async def run_ticks(self) -> None:
        duration = 1.0 / self.coordinator.config.tick_rate
        delay = 0.0
        while True:
            await asyncio.sleep(duration - delay)
            start = monotonic()
            frame = self.coordinator.build_frame()
            self.broadcast(frame.to_wire())
            delay = max(monotonic() - start, 0)

    def broadcast(self, message: dict[str, Any]) -> None:
        if not self.clients:
            return
        self.queue.put_nowait(pack_message(message))

    async def background_broadcast(self) -> None:
        while (payload := await self.queue.get()) is not None:
            results = await asyncio.gather(
                *(c.send(payload) for c in self.clients), return_exceptions=True
            )
            for client, result in zip(self.clients, results):
                if isinstance(result, Exception):
                    self.clients.discard(client)
