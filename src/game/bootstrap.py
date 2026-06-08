from ecs.coordinator import Coordinator
from game.components import Health, Movement, Owner, Position
from game.systems.movement import MovementSystem


def create_coordinator() -> Coordinator:
    coordinator = Coordinator()
    coordinator.register_component(Position)
    coordinator.register_component(Movement)
    coordinator.register_component(Health)
    coordinator.register_component(Owner)
    coordinator.register_system(MovementSystem)
    coordinator.set_system_signature(
        MovementSystem,
        coordinator.make_signature(Position, Movement),
    )
    return coordinator
