from config import InitialStateConfig, MatchConfig
from core.commands import Command, CommandType
from core.types import EntityId, Tick, fixed
from game.bootstrap import build_initial_state
from server.match import MatchCoordinator


def _player_resources(snapshot: dict, player_number: int) -> int:
    for entity in snapshot["entities"]:
        if entity["id"] == player_number:
            return int(entity["Resources"]["amount"])
    raise AssertionError(f"player {player_number} missing")


def _unit_for_owner(snapshot: dict, owner: int) -> dict:
    for entity in snapshot["entities"]:
        if entity.get("OwnedBy", {}).get("owner") == owner:
            return entity
    raise AssertionError(f"unit for owner {owner} missing")


def test_assign_command_uses_fixed_delay() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=3))
    command = Command(type=CommandType.MOVE, issuer=EntityId(1), sequence=1)

    assigned_tick = coordinator.assign_command(command, received_at_tick=Tick(100))

    assert int(assigned_tick) == 103


def test_build_frame_sorts_commands_canonically() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=0))
    coordinator.assign_command(Command(type=CommandType.MOVE, issuer=EntityId(2), sequence=2), Tick(0))
    coordinator.assign_command(Command(type=CommandType.MOVE, issuer=EntityId(1), sequence=1), Tick(0))
    frame = coordinator.build_frame()

    assert [int(command.issuer) for command in frame.commands] == [1, 2]


def test_state_sync_payload_contains_initial_state_and_history() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=0))
    coordinator.assign_command(Command(type=CommandType.MOVE, issuer=EntityId(1), sequence=1), Tick(0))
    coordinator.build_frame()
    payload = coordinator.state_sync_payload()

    assert payload["kind"] == "state_sync"
    assert payload["current_tick"] == 1
    assert _player_resources(payload["initial_state"], 1) == 500
    assert len(payload["command_frames"]) == 1


def test_state_sync_uses_latest_snapshot_as_bootstrap_state() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=0, snapshot_interval_ticks=2))
    config = coordinator.initial_state_config
    unit_id = config.player_count + 1
    command = Command(
        type=CommandType.MOVE,
        issuer=EntityId(1),
        sequence=1,
        targets=(EntityId(unit_id),),
        x=fixed(5),
        y=fixed(4),
    )

    coordinator.assign_command(command, Tick(0))
    coordinator.build_frame()
    coordinator.build_frame()
    payload = coordinator.state_sync_payload()
    unit = _unit_for_owner(payload["snapshot"], 1)

    assert payload["snapshot_tick"] == 2
    assert unit["Position"]["x"] == 4500
    assert unit["Movement"]["target_x"] == fixed(5)


def test_default_initial_state_contains_101_players_as_entities() -> None:
    initial_state = build_initial_state(InitialStateConfig())
    players = [entity for entity in initial_state["entities"] if "Resources" in entity]
    units = [entity for entity in initial_state["entities"] if "OwnedBy" in entity]

    assert initial_state["next_entity_id"] == 203
    assert len(players) == 101
    assert len(units) == 101
    assert _player_resources(initial_state, 101) == 500
    assert _unit_for_owner(initial_state, 101)["OwnedBy"]["owner"] == 101
