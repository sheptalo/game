import asyncio
from dataclasses import dataclass, field
from time import monotonic
from typing import Any


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
