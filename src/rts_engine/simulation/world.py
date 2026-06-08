from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rts_engine.core.checksum import ChecksumBuilder
from rts_engine.core.types import PlayerId, UnitId


@dataclass(slots=True)
class UnitStore:
    ids: list[int] = field(default_factory=list)
    owner: list[str] = field(default_factory=list)
    x: list[int] = field(default_factory=list)
    y: list[int] = field(default_factory=list)
    target_x: list[int] = field(default_factory=list)
    target_y: list[int] = field(default_factory=list)
    speed: list[int] = field(default_factory=list)
    hp: list[int] = field(default_factory=list)
    _index_by_id: dict[int, int] = field(default_factory=dict)

    def add(
        self,
        unit_id: UnitId,
        owner: PlayerId,
        x: int,
        y: int,
        hp: int = 100,
        speed: int = 100,
    ) -> None:
        int_id = int(unit_id)
        if int_id in self._index_by_id:
            raise ValueError(f"duplicate unit id {int_id}")
        self._index_by_id[int_id] = len(self.ids)
        self.ids.append(int_id)
        self.owner.append(str(owner))
        self.x.append(x)
        self.y.append(y)
        self.target_x.append(x)
        self.target_y.append(y)
        self.speed.append(speed)
        self.hp.append(hp)

    def has(self, unit_id: UnitId | int) -> bool:
        return int(unit_id) in self._index_by_id

    def index(self, unit_id: UnitId | int) -> int:
        return self._index_by_id[int(unit_id)]

    def sorted_indices(self) -> list[int]:
        return [self._index_by_id[unit_id] for unit_id in sorted(self.ids)]


@dataclass(slots=True)
class World:
    units: UnitStore = field(default_factory=UnitStore)
    resources: dict[str, int] = field(default_factory=dict)
    next_unit_id: int = 1

    def add_player(self, player_id: PlayerId, resources: int = 500) -> None:
        key = str(player_id)
        self.resources.setdefault(key, resources)

    def spawn_unit(self, owner: PlayerId, x: int, y: int, hp: int = 100, speed: int = 100) -> UnitId:
        unit_id = UnitId(self.next_unit_id)
        self.next_unit_id += 1
        self.units.add(unit_id=unit_id, owner=owner, x=x, y=y, hp=hp, speed=speed)
        return unit_id

    def checksum(self, tick: int) -> str:
        builder = ChecksumBuilder()
        builder.add_int(tick)
        builder.add_int(self.next_unit_id)
        for player_id in sorted(self.resources):
            builder.add_str(player_id)
            builder.add_int(self.resources[player_id])
        for index in self.units.sorted_indices():
            builder.add_int(self.units.ids[index])
            builder.add_str(self.units.owner[index])
            builder.add_int(self.units.x[index])
            builder.add_int(self.units.y[index])
            builder.add_int(self.units.target_x[index])
            builder.add_int(self.units.target_y[index])
            builder.add_int(self.units.hp[index])
        return builder.digest()


def world_from_snapshot(snapshot: dict[str, Any]) -> World:
    world = World(next_unit_id=int(snapshot["next_unit_id"]))
    world.resources.update({str(player_id): int(resources) for player_id, resources in snapshot["resources"].items()})
    for unit in snapshot["units"]:
        unit_id = UnitId(int(unit["id"]))
        world.units.add(
            unit_id=unit_id,
            owner=PlayerId(str(unit["owner"])),
            x=int(unit["x"]),
            y=int(unit["y"]),
            hp=int(unit["hp"]),
            speed=int(unit["speed"]),
        )
        index = world.units.index(unit_id)
        world.units.target_x[index] = int(unit.get("target_x", unit["x"]))
        world.units.target_y[index] = int(unit.get("target_y", unit["y"]))
    return world


def world_to_snapshot(world: World) -> dict[str, Any]:
    return {
        "next_unit_id": world.next_unit_id,
        "resources": dict(sorted(world.resources.items())),
        "units": [
            {
                "id": world.units.ids[index],
                "owner": world.units.owner[index],
                "x": world.units.x[index],
                "y": world.units.y[index],
                "target_x": world.units.target_x[index],
                "target_y": world.units.target_y[index],
                "hp": world.units.hp[index],
                "speed": world.units.speed[index],
            }
            for index in world.units.sorted_indices()
        ],
    }
