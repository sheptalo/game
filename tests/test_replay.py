from core.commands import Command, CommandFrame, CommandType
from core.command_log import CommandLog
from core.types import PlayerId, Tick, UnitId, fixed
from game.loop import SimulationEngine
from game.world import World


def make_engine() -> SimulationEngine:
    world = World()
    world.add_player(PlayerId("p1"))
    world.spawn_unit(PlayerId("p1"), x=0, y=0)
    return SimulationEngine(world=world)


def test_replay_uses_only_command_log() -> None:
    frame = CommandFrame(
        tick=Tick(2),
        commands=(
            Command(
                type=CommandType.MOVE,
                player_id=PlayerId("p1"),
                sequence=1,
                units=(UnitId(1),),
                x=fixed(3),
                y=fixed(4),
            ),
        ),
    )
    command_log = CommandLog()
    command_log.append(frame)

    first_checksum = command_log.replay(make_engine(), Tick(30))
    second_checksum = command_log.replay(make_engine(), Tick(30))

    assert first_checksum == second_checksum
