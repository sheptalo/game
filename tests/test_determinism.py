import esper

from config import InitialStateConfig, SimulationConfig
from core.checksum import checksum_snapshot
from core.commands import Command, CommandFrame, CommandType
from core.types import EntityId, Tick, fixed
from game.bootstrap import build_initial_state
from game.components import Position
from game.loop import SimulationEngine
from game.world import World


def make_world() -> World:
    config = InitialStateConfig(
        player_count=2,
        grid_columns=2,
        spawn_start_x=0,
        spawn_start_y=0,
        spawn_step_x=fixed(20),
        spawn_step_y=0,
        unit_speed=100,
    )
    return World.from_snapshot(build_initial_state(config))


def test_same_commands_produce_same_checksum() -> None:
    move = Command(
        type=CommandType.MOVE,
        issuer=EntityId(1),
        sequence=2,
        targets=(EntityId(3),),
        x=fixed(10),
        y=fixed(0),
    )
    second_move = Command(
        type=CommandType.MOVE,
        issuer=EntityId(2),
        sequence=1,
        targets=(EntityId(4),),
        x=fixed(15),
        y=fixed(0),
    )
    left = SimulationEngine(world=make_world(), config=SimulationConfig(checksum_interval=1))
    right = SimulationEngine(world=make_world(), config=SimulationConfig(checksum_interval=1))

    left_frame = CommandFrame(tick=Tick(0), commands=(move, second_move))
    right_frame = CommandFrame(tick=Tick(0), commands=(second_move, move))
    for engine, frame in ((left, left_frame), (right, right_frame)):
        engine.step(frame)
        engine.run_until(Tick(20), {})

    assert left.state_checksum() == right.state_checksum()


def test_checksum_ignores_component_registration_details() -> None:
    snapshot = {
        "next_entity_id": 3,
        "entities": [
            {"id": 1, "Resources": {"amount": 500}},
            {
                "id": 2,
                "OwnedBy": {"owner": 1},
                "Position": {"x": 0, "y": 0},
                "Movement": {"target_x": 10, "target_y": 0, "speed": 100},
            },
        ],
    }
    first = checksum_snapshot(5, snapshot)
    extended = {
        **snapshot,
        "entities": [
            snapshot["entities"][0],
            {
                **snapshot["entities"][1],
                "Movement": {"target_x": 10, "target_y": 0, "speed": 100},
            },
        ],
    }
    assert first == checksum_snapshot(5, extended)


def test_integer_movement_reaches_target() -> None:
    engine = SimulationEngine(world=make_world())
    frame = CommandFrame(
        tick=Tick(0),
        commands=(
            Command(
                type=CommandType.MOVE,
                issuer=EntityId(1),
                sequence=1,
                targets=(EntityId(3),),
                x=fixed(1),
                y=0,
            ),
        ),
    )

    engine.step(frame)
    engine.run_until(Tick(10), {})

    with engine.world.bind():
        position = esper.component_for_entity(3, Position)
    assert position.x == fixed(1)
