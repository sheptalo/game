from src.core.commands import Command, CommandFrame, CommandType
from src.core.types import PlayerId, Tick, UnitId, fixed
from src.config import SimulationConfig
from src.game.components import Position
from src.game.loop import SimulationEngine
from src.game.world import World


def make_world() -> World:
    world = World()
    world.add_player(PlayerId("p1"))
    world.add_player(PlayerId("p2"))
    world.spawn_unit(PlayerId("p1"), x=0, y=0)
    world.spawn_unit(PlayerId("p2"), x=fixed(20), y=0)
    return world


def test_same_commands_produce_same_checksum_independent_of_input_order() -> None:
    move = Command(
        type=CommandType.MOVE,
        player_id=PlayerId("p1"),
        sequence=2,
        units=(UnitId(1),),
        x=fixed(10),
        y=fixed(0),
    )
    second_move = Command(
        type=CommandType.MOVE,
        player_id=PlayerId("p2"),
        sequence=1,
        units=(UnitId(2),),
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

    assert left.world.checksum(int(left.tick)) == right.world.checksum(int(right.tick))


def test_integer_movement_reaches_target_without_float_math() -> None:
    engine = SimulationEngine(world=make_world())
    frame = CommandFrame(
        tick=Tick(0),
        commands=(
            Command(
                type=CommandType.MOVE,
                player_id=PlayerId("p1"),
                sequence=1,
                units=(UnitId(1),),
                x=fixed(1),
                y=0,
            ),
        ),
    )

    engine.step(frame)
    engine.run_until(Tick(10), {})

    position = engine.world.coordinator.get_component(1, Position)
    assert position.x == fixed(1)
    assert position.y == 0
