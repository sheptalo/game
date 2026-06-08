from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.checksum import ChecksumBuilder
from core.types import EntityId, PlayerId
from ecs.coordinator import Coordinator
from game.bootstrap import create_coordinator
from game.components import Health, Movement, Owner, Position


@dataclass(slots=True)
class World:
    coordinator: Coordinator = field(default_factory=create_coordinator)
    resources: dict[str, int] = field(default_factory=dict)

    def add_player(self, player_id: PlayerId, resources: int = 500) -> None:
        key = str(player_id)
        self.resources.setdefault(key, resources)

    def spawn_unit(
        self,
        owner: PlayerId,
        x: int,
        y: int,
        hp: int = 100,
        speed: int = 100,
    ) -> EntityId:
        entity = self.coordinator.create_entity()
        self.coordinator.add_component(entity, Owner(str(owner)))
        self.coordinator.add_component(entity, Position(x, y))
        self.coordinator.add_component(entity, Movement(x, y, speed))
        self.coordinator.add_component(entity, Health(hp))
        return EntityId(entity)

    def destroy_entity(self, entity: EntityId | int) -> None:
        self.coordinator.destroy_entity(int(entity))

    def checksum(self, tick: int) -> str:
        builder = ChecksumBuilder()
        builder.add_int(tick)
        builder.add_int(self.coordinator.entity_manager.next_id)
        for player_id in sorted(self.resources):
            builder.add_str(player_id)
            builder.add_int(self.resources[player_id])
        for entity in self.coordinator.living_entities_sorted():
            if not self._is_unit(entity):
                continue
            builder.add_int(entity)
            builder.add_str(self.coordinator.get_component(entity, Owner).player_id)
            position = self.coordinator.get_component(entity, Position)
            movement = self.coordinator.get_component(entity, Movement)
            builder.add_int(position.x)
            builder.add_int(position.y)
            builder.add_int(movement.target_x)
            builder.add_int(movement.target_y)
            builder.add_int(self.coordinator.get_component(entity, Health).hp)
        return builder.digest()

    def _is_unit(self, entity: int) -> bool:
        return (
            self.coordinator.has_component(entity, Owner)
            and self.coordinator.has_component(entity, Position)
            and self.coordinator.has_component(entity, Movement)
            and self.coordinator.has_component(entity, Health)
        )


def world_from_snapshot(snapshot: dict[str, Any]) -> World:
    world = World()
    world.coordinator.entity_manager.next_id = int(snapshot["next_unit_id"])
    world.resources.update(
        {str(player_id): int(resources) for player_id, resources in snapshot["resources"].items()}
    )
    for unit in snapshot["units"]:
        entity = world.coordinator.register_entity(int(unit["id"]))
        world.coordinator.add_component(entity, Owner(str(unit["owner"])))
        world.coordinator.add_component(entity, Position(int(unit["x"]), int(unit["y"])))
        world.coordinator.add_component(
            entity,
            Movement(
                int(unit.get("target_x", unit["x"])),
                int(unit.get("target_y", unit["y"])),
                int(unit["speed"]),
            ),
        )
        world.coordinator.add_component(entity, Health(int(unit["hp"])))
    return world


def world_to_snapshot(world: World) -> dict[str, Any]:
    return {
        "next_unit_id": world.coordinator.entity_manager.next_id,
        "resources": dict(sorted(world.resources.items())),
        "units": [
            {
                "id": entity,
                "owner": world.coordinator.get_component(entity, Owner).player_id,
                "x": world.coordinator.get_component(entity, Position).x,
                "y": world.coordinator.get_component(entity, Position).y,
                "target_x": world.coordinator.get_component(entity, Movement).target_x,
                "target_y": world.coordinator.get_component(entity, Movement).target_y,
                "hp": world.coordinator.get_component(entity, Health).hp,
                "speed": world.coordinator.get_component(entity, Movement).speed,
            }
            for entity in world.coordinator.living_entities_sorted()
            if world._is_unit(entity)
        ],
    }
