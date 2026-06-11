import asyncio
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from websockets import ConnectionClosedError
from websockets.asyncio.server import broadcast as websockets_broadcast
from websockets.exceptions import ConnectionClosedOK

from game.protocol import command_from_client_wire
from server.match import MatchCoordinator
from server.protocol import pack_message, unpack_message


@dataclass(slots=True)
class LockstepServer:
    coordinator: MatchCoordinator = field(default_factory=MatchCoordinator)
    clients: set[Any] = field(default_factory=set)

    async def handler(self, websocket: Any) -> None:
        self.clients.add(websocket)
        await websocket.send(pack_message(self.coordinator.resync_payload()))
        try:
            async for payload in websocket:
                try:
                    await self._handle_message(websocket, payload)
                except (ValueError, KeyError, TypeError) as error:
                    await websocket.send(
                        pack_message({"kind": "error", "detail": str(error)})
                    )
        except (ConnectionClosedError, ConnectionClosedOK):
            pass
        finally:
            self.clients.discard(websocket)

    async def _handle_message(self, websocket: Any, payload: bytes) -> None:
        message = unpack_message(payload)
        kind = message.get("kind")
        if kind == "state_sync_request":
            await websocket.send(pack_message(self.coordinator.resync_payload()))
        elif kind == "checksum":
            report = self.coordinator.record_checksum(
                player_id=str(message["player_id"]),
                tick=int(message["tick"]),
                checksum=str(message["checksum"]),
            )
            if report is not None:
                self.broadcast(report)
        elif kind == "command":
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

    async def run_ticks(self) -> None:
        duration = 1.0 / self.coordinator.config.tick_rate
        # Absolute deadlines: sleep overshoot and slow frames shrink the next
        # sleep instead of accumulating as tick-rate drift.
        next_tick = monotonic() + duration
        while True:
            await asyncio.sleep(max(next_tick - monotonic(), 0))
            next_tick += duration
            frame = self.coordinator.build_frame()
            self.broadcast(frame.to_wire())

    def broadcast(self, message: dict[str, Any]) -> None:
        if not self.clients:
            return
        # Serializes the frame once and writes synchronously to every open
        # connection; closed connections are skipped and removed by handler().
        websockets_broadcast(self.clients, pack_message(message))
