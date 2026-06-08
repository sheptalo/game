from src.core.types import PlayerId
from src.ecs.coordinator import Coordinator
from src.game.components import Movement, Owner, Position
from src.game.systems.movement import MovementSystem
from src.game.world import World


def test_movement_system_skips_entities_without_required_components() -> None:
    world = World()
    movable = world.coordinator.create_entity()
    world.coordinator.add_component(movable, Position(0, 0))
    world.coordinator.add_component(movable, Movement(100, 0, 100))

    static = world.coordinator.create_entity()
    world.coordinator.add_component(static, Position(5, 5))

    movement = world.coordinator.get_system(MovementSystem)
    movement.update(world.coordinator)

    assert movable in movement.entities
    assert static not in movement.entities
    assert world.coordinator.get_component(movable, Position).x == 100
    assert world.coordinator.get_component(static, Position).x == 5


def test_destroy_entity_recycles_id_and_clears_components() -> None:
    world = World()
    first = int(world.spawn_unit(PlayerId("p1"), x=0, y=0))
    second = int(world.spawn_unit(PlayerId("p1"), x=10, y=0))

    world.destroy_entity(first)
    assert not world.coordinator.has_entity(first)
    assert not world.coordinator.has_component(first, Position)

    third = world.coordinator.create_entity()
    assert third == first
    assert first not in world.coordinator.get_system(MovementSystem).entities

    world.coordinator.add_component(third, Owner("p1"))
    world.coordinator.add_component(third, Position(0, 0))
    world.coordinator.add_component(third, Movement(50, 0, 100))
    movement = world.coordinator.get_system(MovementSystem)
    assert third in movement.entities
    assert second in movement.entities


def test_coordinator_signature_tracks_optional_components() -> None:
    world = World()
    entity = world.coordinator.create_entity()
    world.coordinator.add_component(entity, Position(1, 2))

    signature = world.coordinator.entity_manager.get_signature(entity)
    movement_type = world.coordinator.component_manager.get_component_type(Movement)

    assert signature.contains(world.coordinator.make_signature(Position))
    assert not signature.contains(world.coordinator.make_signature(Position, Movement))

    world.coordinator.add_component(entity, Movement(1, 2, 100))
    signature = world.coordinator.entity_manager.get_signature(entity)
    assert signature.contains(world.coordinator.make_signature(Position, Movement))
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
