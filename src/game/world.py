from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.checksum import ChecksumBuilder
from core.types import EntityId, PlayerId
from ecs.coordinator import Coordinator
from game.components import Health, Movement, Owner, Position
from game.systems.movement import MovementSystem


def create_coordinator() -> Coordinator:
    coordinator = Coordinator()
    for component in (Position, Movement, Health, Owner):
        coordinator.register_component(component)
    coordinator.register_system(MovementSystem)
    coordinator.set_system_signature(
        MovementSystem,
        coordinator.make_signature(Position, Movement),
    )
    return coordinator


@dataclass(slots=True)
class World:
    coordinator: Coordinator = field(default_factory=create_coordinator)
    resources: dict[str, int] = field(default_factory=dict)

    def add_player(self, player_id: PlayerId, resources: int = 500) -> None:
        self.resources.setdefault(str(player_id), resources)

    def spawn_unit(
        self,
        owner: PlayerId,
        x: int,
        y: int,
        hp: int = 100,
        speed: int = 100,
    ) -> EntityId:
        entity = self.coordinator.create_entity()
        ecs = self.coordinator
        ecs.add_component(entity, Owner(str(owner)))
        ecs.add_component(entity, Position(x, y))
        ecs.add_component(entity, Movement(x, y, speed))
        ecs.add_component(entity, Health(hp))
        return EntityId(entity)

    def destroy_entity(self, entity: EntityId | int) -> None:
        self.coordinator.destroy_entity(int(entity))

    def checksum(self, tick: int) -> str:
        builder = ChecksumBuilder()
        builder.add_int(tick)
        builder.add_int(self.coordinator.next_entity_id)
        for player_id in sorted(self.resources):
            builder.add_str(player_id)
            builder.add_int(self.resources[player_id])
        for entity in self.coordinator.living_entities_sorted():
            if not _is_unit(self.coordinator, entity):
                continue
            owner = self.coordinator.get_component(entity, Owner)
            position = self.coordinator.get_component(entity, Position)
            movement = self.coordinator.get_component(entity, Movement)
            health = self.coordinator.get_component(entity, Health)
            builder.add_int(entity)
            builder.add_str(owner.player_id)
            builder.add_int(position.x)
            builder.add_int(position.y)
            builder.add_int(movement.target_x)
            builder.add_int(movement.target_y)
            builder.add_int(health.hp)
        return builder.digest()


def _is_unit(ecs: Coordinator, entity: int) -> bool:
    return all(
        ecs.has_component(entity, component)
        for component in (Owner, Position, Movement, Health)
    )


def world_from_snapshot(snapshot: dict[str, Any]) -> World:
    world = World()
    world.coordinator.next_entity_id = int(snapshot["next_unit_id"])
    world.resources.update(
        {str(player_id): int(resources) for player_id, resources in snapshot["resources"].items()}
    )
    for unit in snapshot["units"]:
        entity = world.coordinator.register_entity(int(unit["id"]))
        ecs = world.coordinator
        ecs.add_component(entity, Owner(str(unit["owner"])))
        ecs.add_component(entity, Position(int(unit["x"]), int(unit["y"])))
        ecs.add_component(
            entity,
            Movement(
                int(unit.get("target_x", unit["x"])),
                int(unit.get("target_y", unit["y"])),
                int(unit["speed"]),
            ),
        )
        ecs.add_component(entity, Health(int(unit["hp"])))
    return world


def world_to_snapshot(world: World) -> dict[str, Any]:
    ecs = world.coordinator
    return {
        "next_unit_id": ecs.next_entity_id,
        "resources": dict(sorted(world.resources.items())),
        "units": [
            {
                "id": entity,
                "owner": ecs.get_component(entity, Owner).player_id,
                "x": ecs.get_component(entity, Position).x,
                "y": ecs.get_component(entity, Position).y,
                "target_x": ecs.get_component(entity, Movement).target_x,
                "target_y": ecs.get_component(entity, Movement).target_y,
                "hp": ecs.get_component(entity, Health).hp,
                "speed": ecs.get_component(entity, Movement).speed,
            }
            for entity in ecs.living_entities_sorted()
            if _is_unit(ecs, entity)
        ],
    }
