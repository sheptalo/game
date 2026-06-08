from __future__ import annotations

import argparse
import asyncio
import contextlib
import math
from dataclasses import dataclass
from typing import Any

import msgpack


SCALE = 1000


@dataclass(frozen=True, slots=True)
class BotConfig:
    url: str
    first_player: int
    count: int
    command_interval: float
    radius: int


def pack_message(message: dict[str, Any]) -> bytes:
    return msgpack.packb(message, use_bin_type=True, strict_types=True)


def unpack_message(payload: bytes) -> dict[str, Any]:
    message = msgpack.unpackb(payload, raw=False, strict_map_key=False)
    if not isinstance(message, dict):
        raise ValueError("wire message must be a map")
    return message


def find_unit_id(snapshot: dict[str, Any], player_number: int) -> int:
    for entity in snapshot["entities"]:
        owner = entity.get("OwnedBy", {}).get("owner")
        if owner == player_number:
            return int(entity["id"])
    raise ValueError(f"no unit found for player {player_number}")


def find_spawn(snapshot: dict[str, Any], unit_id: int) -> tuple[int, int]:
    for entity in snapshot["entities"]:
        if int(entity.get("id", -1)) == unit_id:
            position = entity["Position"]
            return int(position["x"]), int(position["y"])
    raise ValueError(f"no unit found for {unit_id}")


def next_target(
    spawn_x: int, spawn_y: int, player_number: int, sequence: int, radius: int
) -> tuple[int, int]:
    angle = (sequence * 1.618 + player_number * 0.37) % (math.pi * 2)
    x = spawn_x + int(math.cos(angle) * radius * SCALE)
    y = spawn_y + int(math.sin(angle) * radius * SCALE)
    return max(0, x), max(0, y)


async def receive_loop(websocket: Any) -> None:
    async for payload in websocket:
        if isinstance(payload, bytes):
            unpack_message(payload)


async def run_bot(config: BotConfig, player_number: int) -> None:
    try:
        import websockets
    except ImportError as error:
        raise RuntimeError("websockets is required to run bots") from error

    player_id = f"p{player_number}"
    async with websockets.connect(config.url, max_queue=128) as websocket:
        sync_payload = await websocket.recv()
        if isinstance(sync_payload, str):
            raise ValueError("expected binary state_sync")
        sync = unpack_message(sync_payload)
        if sync.get("kind") != "state_sync":
            raise ValueError(f"expected state_sync, got {sync.get('kind')!r}")

        snapshot = sync.get("snapshot") or sync["initial_state"]
        unit_id = find_unit_id(snapshot, player_number)
        spawn_x, spawn_y = find_spawn(snapshot, unit_id)
        receiver = asyncio.create_task(receive_loop(websocket))
        sequence = 1
        try:
            while True:
                x, y = next_target(
                    spawn_x, spawn_y, player_number, sequence, config.radius
                )
                command = {
                    "type": "MOVE",
                    "player_id": player_id,
                    "sequence": sequence,
                    "units": [unit_id],
                    "x": x,
                    "y": y,
                }
                await websocket.send(
                    pack_message({"kind": "command", "command": command})
                )
                sequence += 1
                await asyncio.sleep(config.command_interval)
        finally:
            receiver.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receiver


async def run_swarm(config: BotConfig) -> None:
    tasks = [
        asyncio.create_task(run_bot(config, player_number))
        for player_number in range(
            config.first_player, config.first_player + config.count
        )
    ]
    print(
        f"started {config.count} bots: "
        f"p{config.first_player}..p{config.first_player + config.count - 1}"
    )
    await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RTS websocket bot swarm")
    parser.add_argument("--url", default="ws://127.0.0.1:8765")
    parser.add_argument("--first-player", type=int, default=1)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--command-interval", type=float, default=0.05)
    parser.add_argument("--radius", type=int, default=12)
    args = parser.parse_args()
    asyncio.run(
        run_swarm(
            BotConfig(
                url=args.url,
                first_player=args.first_player,
                count=args.count,
                command_interval=args.command_interval,
                radius=args.radius,
            )
        )
    )


if __name__ == "__main__":
    main()
