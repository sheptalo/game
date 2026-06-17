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

_AUTH_TIMEOUT_SECONDS: float = 10.0


@dataclass(slots=True)
class LockstepServer:
    coordinator: MatchCoordinator = field(default_factory=MatchCoordinator)
    clients: set[Any] = field(default_factory=set)
    _connections: dict[Any, Any] = field(default_factory=dict)

    async def handler(self, websocket: Any) -> None:
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=_AUTH_TIMEOUT_SECONDS)
            message = unpack_message(raw)
            if message.get("kind") != "auth":
                await websocket.close()
                return
            token = str(message.get("token", ""))
            if not token:
                await websocket.close()
                return
        except (TimeoutError, ConnectionClosedError, ConnectionClosedOK):
            return

        player_id = self.coordinator.authenticate(token)
        if player_id is None:
            await websocket.close()
            return
        self._connections[websocket] = player_id
        self.clients.add(websocket)
        await websocket.send(pack_message(self.coordinator.resync_payload(player_id)))
        try:
            async for payload in websocket:
                try:
                    await self._handle_message(websocket, payload)
                except (ValueError, KeyError, TypeError):
                    await websocket.send(pack_message({"kind": "error"}))
        except (ConnectionClosedError, ConnectionClosedOK):
            pass
        finally:
            self.clients.discard(websocket)
            self._connections.pop(websocket, None)

    async def _handle_message(self, websocket: Any, payload: bytes) -> None:
        message = unpack_message(payload)
        kind = message.get("kind")
        if kind == "state_sync_request":
            player_id = self._connections.get(websocket)
            await websocket.send(pack_message(self.coordinator.resync_payload(player_id)))
        elif kind == "checksum":
            player_id = self._connections.get(websocket)
            if player_id is None:
                return
            report = self.coordinator.record_checksum(
                player_id=str(int(player_id)),
                tick=int(message["tick"]),
                checksum=str(message["checksum"]),
            )
            if report is not None:
                self.broadcast(report)
        elif kind == "command":
            player_id = self._connections.get(websocket)
            if player_id is None:
                return
            command = command_from_client_wire(message["command"], player_id)
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
        next_tick = monotonic() + duration
        while True:
            await asyncio.sleep(max(next_tick - monotonic(), 0))
            next_tick += duration
            frame = self.coordinator.build_frame()
            self.broadcast(frame.to_wire())

    def broadcast(self, message: dict[str, Any]) -> None:
        if not self.clients:
            return
        websockets_broadcast(self.clients, pack_message(message))
