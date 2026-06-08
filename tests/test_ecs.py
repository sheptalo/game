import esper

from core.types import EntityId
from game.components import Movement, OwnedBy, Position, Resources
from game.systems.movement import MovementProcessor
from game.world import World


def test_world_create_and_snapshot_roundtrip() -> None:
    world = World()
    world.create(1, Resources(500))
    world.create(2, OwnedBy(EntityId(1)), Position(0, 0), Movement(0, 0, 100))

    restored = World.from_snapshot(world.to_snapshot())
    with restored.bind():
        assert esper.component_for_entity(1, Resources).amount == 500
        assert esper.component_for_entity(2, OwnedBy).owner == EntityId(1)


def test_movement_processor_runs_in_world_context() -> None:
    world = World()
    world.create(1, Position(0, 0), Movement(100, 0, 100))
    with world.bind():
        esper.get_processor(MovementProcessor).process()
        assert esper.component_for_entity(1, Position).x == 100
