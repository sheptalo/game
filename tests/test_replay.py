from config import InitialStateConfig
from core.commands import Command, CommandFrame, CommandType
from core.types import EntityId, Tick, fixed
from game.bootstrap import build_initial_state
from game.loop import SimulationEngine
from game.world import World


def test_replay_produces_same_checksum() -> None:
    world = World.from_snapshot(build_initial_state(InitialStateConfig(player_count=1)))
    frame = CommandFrame(
        tick=Tick(2),
        commands=(
            Command(
                type=CommandType.MOVE,
                issuer=EntityId(1),
                sequence=1,
                targets=(EntityId(2),),
                x=fixed(3),
                y=fixed(4),
            ),
        ),
    )
    frames = {2: frame}

    first = SimulationEngine(world=world)
    first.run_until(Tick(30), frames)
    checksum = first.state_checksum()

    second = SimulationEngine(world=World.from_snapshot(build_initial_state(InitialStateConfig(player_count=1))))
    second.run_until(Tick(30), frames)

    assert second.state_checksum() == checksum
