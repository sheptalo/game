from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from config import InitialStateConfig, MatchConfig
from core.checksum import checksum_snapshot
from core.commands import Command, CommandFrame, canonical_commands
from core.types import Tick
from game import world
from game.simulation import step as simulation_step


@dataclass(slots=True)
class MatchCoordinator:
    config: MatchConfig = field(default_factory=MatchConfig)
    game_config: InitialStateConfig = field(default_factory=InitialStateConfig)
    tick: Tick = Tick(0)
    _pending: dict[int, list[Command]] = field(default_factory=lambda: defaultdict(list))
    _issuer_counts: dict[tuple[int, int], int] = field(default_factory=dict)
    _history: dict[int, CommandFrame] = field(default_factory=dict)
    _checksums: dict[int, dict[str, set[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(set))
    )
    _reported_desync_ticks: set[int] = field(default_factory=set)
    _server_checksum_label: str = "__server__"
    _snapshot_tick: Tick = Tick(0)
    _snapshot: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        world.init(self.game_config)
        self._snapshot = world.snapshot()

    def assign_command(self, command: Command, received_at_tick: Tick | None = None) -> Tick:
        base_tick = int(self.tick if received_at_tick is None else received_at_tick)
        target_tick = Tick(base_tick + self.config.command_delay_ticks)
        key = (int(command.issuer), int(target_tick))
        count = self._issuer_counts.get(key, 0)
        if count >= self.config.max_commands_per_player_per_tick:
            raise ValueError(
                f"too many commands from issuer {command.issuer} for tick {int(target_tick)}"
            )
        self._issuer_counts[key] = count + 1
        self._pending[int(target_tick)].append(command)
        return target_tick

    def build_frame(self) -> CommandFrame:
        commands = tuple(canonical_commands(self._pending.pop(int(self.tick), ())))
        frame = CommandFrame(tick=self.tick, commands=commands)
        if frame.commands:
            self._history[int(frame.tick)] = frame

        simulation_step(frame.commands)
        self._record_server_checksum()
        self.tick = Tick(int(self.tick) + 1)
        self._maybe_store_snapshot()
        self._prune_history()
        return frame

    def state_sync_payload(self) -> dict[str, Any]:
        snapshot_tick = int(self._snapshot_tick)
        return self._sync_payload(snapshot_tick, self._snapshot)

    def resync_payload(self) -> dict[str, Any]:
        snapshot_tick = int(self.tick)
        snapshot = world.snapshot()
        self._snapshot_tick = Tick(snapshot_tick)
        self._snapshot = snapshot
        self._prune_history()
        self._prune_checksums()
        return self._sync_payload(snapshot_tick, snapshot)

    def _sync_payload(
        self, snapshot_tick: int, snapshot: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "kind": "state_sync",
            "current_tick": int(self.tick),
            "snapshot_tick": snapshot_tick,
            "tick_rate": self.config.tick_rate,
            "command_delay_ticks": self.config.command_delay_ticks,
            "checksum_interval_ticks": self.config.checksum_interval_ticks,
            "game_config": asdict(self.game_config),
            "snapshot": snapshot,
            "command_frames": [
                frame.to_wire()
                for frame in self.history_frames(from_tick=snapshot_tick)
            ],
        }

    def history_frames(self, from_tick: Tick | int = 0) -> list[CommandFrame]:
        start = int(from_tick)
        return [self._history[tick] for tick in sorted(self._history) if tick >= start]

    def record_checksum(
        self, player_id: str, tick: Tick | int, checksum: str
    ) -> dict[str, Any] | None:
        int_tick = int(tick)
        self._checksums[int_tick][str(checksum)].add(str(player_id))
        self._prune_checksums()

        if int_tick in self._reported_desync_ticks or len(self._checksums[int_tick]) <= 1:
            return None

        self._reported_desync_ticks.add(int_tick)
        return {
            "kind": "desync_report",
            "tick": int_tick,
            "checksums": {
                value: sorted(players)
                for value, players in sorted(self._checksums[int_tick].items())
            },
        }

    def _prune_history(self) -> None:
        cutoff = int(self._snapshot_tick)
        if cutoff <= 0:
            return
        for tick in [tick for tick in self._history if tick < cutoff]:
            del self._history[tick]

    def _prune_checksums(self) -> None:
        cutoff = int(self._snapshot_tick)
        if cutoff <= 0:
            return
        for tick in [tick for tick in self._checksums if tick < cutoff]:
            del self._checksums[tick]
            self._reported_desync_ticks.discard(tick)

    def _record_server_checksum(self) -> None:
        interval = self.config.checksum_interval_ticks
        tick = int(self.tick)
        if interval <= 0 or tick <= 0 or tick % interval != 0:
            return
        checksum = checksum_snapshot(tick, world.snapshot())
        self._checksums[tick][checksum].add(self._server_checksum_label)

    def _maybe_store_snapshot(self) -> None:
        interval = self.config.snapshot_interval_ticks
        if interval <= 0:
            return
        tick = int(self.tick)
        if tick > 0 and tick % interval == 0:
            self._snapshot_tick = Tick(tick)
            self._snapshot = world.snapshot()
