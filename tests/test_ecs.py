from core.types import PlayerId
from ecs.coordinator import Coordinator
from game.components import Movement, Owner, Position
from game.systems.movement import MovementSystem
from game.world import World


def test_movement_system_skips_entities_without_required_components() -> None:
    world = World()
    ecs = world.coordinator
    movable = ecs.create_entity()
    ecs.add_component(movable, Position(0, 0))
    ecs.add_component(movable, Movement(100, 0, 100))

    static = ecs.create_entity()
    ecs.add_component(static, Position(5, 5))

    movement = ecs.get_system(MovementSystem)
    movement.update(ecs)

    assert movable in movement.entities
    assert static not in movement.entities
    assert ecs.get_component(movable, Position).x == 100
    assert ecs.get_component(static, Position).x == 5


def test_destroy_entity_recycles_id_and_clears_components() -> None:
    world = World()
    ecs = world.coordinator
    first = int(world.spawn_unit(PlayerId("p1"), x=0, y=0))
    second = int(world.spawn_unit(PlayerId("p1"), x=10, y=0))

    world.destroy_entity(first)
    assert not ecs.has_entity(first)
    assert not ecs.has_component(first, Position)

    third = ecs.create_entity()
    assert third == first
    assert first not in ecs.get_system(MovementSystem).entities

    ecs.add_component(third, Owner("p1"))
    ecs.add_component(third, Position(0, 0))
    ecs.add_component(third, Movement(50, 0, 100))
    movement = ecs.get_system(MovementSystem)
    assert third in movement.entities
    assert second in movement.entities


def test_coordinator_signature_tracks_optional_components() -> None:
    world = World()
    ecs = world.coordinator
    entity = ecs.create_entity()
    ecs.add_component(entity, Position(1, 2))

    signature = ecs.entity_signature(entity)
    movement_type = ecs.component_type_id(Movement)

    assert signature.contains(ecs.make_signature(Position))
    assert not signature.contains(ecs.make_signature(Position, Movement))

    ecs.add_component(entity, Movement(1, 2, 100))
    signature = ecs.entity_signature(entity)
    assert signature.contains(ecs.make_signature(Position, Movement))
    assert signature.value & (1 << movement_type)


def test_ecs_package_is_game_agnostic() -> None:
    coordinator = Coordinator()
    coordinator.register_component(Position)
    coordinator.register_system(MovementSystem)
    coordinator.set_system_signature(
        MovementSystem,
        coordinator.make_signature(Position),
    )

    entity = coordinator.create_entity()
    coordinator.add_component(entity, Position(1, 2))
    assert entity in coordinator.get_system(MovementSystem).entities
