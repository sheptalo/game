from src.core.commands import Command, CommandType
from src.core.types import PlayerId, Tick, UnitId, fixed
from src.config import MatchConfig
from src.server.match import MatchCoordinator, default_initial_state


def test_assign_command_uses_fixed_delay() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=3))
    command = Command(type=CommandType.MOVE, player_id=PlayerId("p1"), sequence=1)

    assigned_tick = coordinator.assign_command(command, received_at_tick=Tick(100))

    assert int(assigned_tick) == 103


def test_build_frame_sorts_commands_canonically() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=0))
    second = Command(type=CommandType.MOVE, player_id=PlayerId("p2"), sequence=2)
    first = Command(type=CommandType.MOVE, player_id=PlayerId("p1"), sequence=1)

    coordinator.assign_command(second, received_at_tick=Tick(0))
    coordinator.assign_command(first, received_at_tick=Tick(0))
    frame = coordinator.build_frame()

    assert [command.player_id for command in frame.commands] == ["p1", "p2"]


def test_state_sync_payload_contains_initial_state_and_history() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=0))
    command = Command(type=CommandType.MOVE, player_id=PlayerId("p1"), sequence=1)

    coordinator.assign_command(command, received_at_tick=Tick(0))
    coordinator.build_frame()
    payload = coordinator.state_sync_payload()

    assert payload["kind"] == "state_sync"
    assert payload["current_tick"] == 1
    assert payload["game_config"]["player_count"] == 101
    assert payload["checksum_interval_ticks"] == 100
    assert payload["initial_state"]["resources"]["p1"] == 500
    assert len(payload["command_frames"]) == 1
    assert payload["command_frames"][0]["commands"][0]["sequence"] == 1


def test_state_sync_uses_latest_snapshot_as_bootstrap_state() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=0, snapshot_interval_ticks=2))
    command = Command(
        type=CommandType.MOVE,
        player_id=PlayerId("p1"),
        sequence=1,
        units=(UnitId(1),),
        x=fixed(5),
        y=fixed(4),
    )

    coordinator.assign_command(command, received_at_tick=Tick(0))
    coordinator.build_frame()
    coordinator.build_frame()
    payload = coordinator.state_sync_payload()

    assert payload["current_tick"] == 2
    assert payload["snapshot_tick"] == 2
    assert payload["snapshot"]["units"][0]["x"] == 4500
    assert payload["snapshot"]["units"][0]["target_x"] == fixed(5)
    assert payload["command_frames"] == []


def test_state_sync_retains_only_command_tail_after_snapshot() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(command_delay_ticks=0, snapshot_interval_ticks=2))
    early = Command(type=CommandType.MOVE, player_id=PlayerId("p1"), sequence=1)
    tail = Command(type=CommandType.MOVE, player_id=PlayerId("p1"), sequence=2)

    coordinator.assign_command(early, received_at_tick=Tick(0))
    coordinator.build_frame()
    coordinator.build_frame()
    coordinator.assign_command(tail, received_at_tick=Tick(2))
    coordinator.build_frame()
    payload = coordinator.state_sync_payload()

    assert payload["snapshot_tick"] == 2
    assert [frame["tick"] for frame in payload["command_frames"]] == [2]
    assert payload["command_frames"][0]["commands"][0]["sequence"] == 2


def test_default_initial_state_contains_101_single_unit_players() -> None:
    initial_state = default_initial_state()

    assert initial_state["next_unit_id"] == 102
    assert len(initial_state["resources"]) == 101
    assert len(initial_state["units"]) == 101
    assert initial_state["resources"]["p101"] == 500
    assert initial_state["units"][-1]["owner"] == "p101"


def test_matching_checksums_do_not_report_desync() -> None:
    coordinator = MatchCoordinator()

    assert coordinator.record_checksum("p1", Tick(100), "abc123") is None
    assert coordinator.record_checksum("p2", Tick(100), "abc123") is None


def test_mismatched_checksums_report_desync_once() -> None:
    coordinator = MatchCoordinator()

    assert coordinator.record_checksum("p1", Tick(100), "left") is None
    report = coordinator.record_checksum("p2", Tick(100), "right")
    duplicate = coordinator.record_checksum("p3", Tick(100), "third")

    assert report == {
        "kind": "desync_report",
        "tick": 100,
        "checksums": {
            "left": ["p1"],
            "right": ["p2"],
        },
    }
    assert duplicate is None


def test_single_client_checksum_is_compared_with_server_baseline() -> None:
    coordinator = MatchCoordinator(config=MatchConfig(checksum_interval_ticks=2))

    coordinator.build_frame()
    coordinator.build_frame()
    report = coordinator.record_checksum("p1", Tick(2), "wrong")

    assert report is not None
    assert report["kind"] == "desync_report"
    assert report["tick"] == 2
    assert report["checksums"]["wrong"] == ["p1"]
    assert "__server__" in {
        player_id
        for players in report["checksums"].values()
        for player_id in players
    }
