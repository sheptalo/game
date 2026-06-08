from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from config import InitialStateConfig, MatchConfig, game_config_payload
from core.checksum import checksum_snapshot
from core.commands import Command, CommandFrame, canonical_commands
from core.types import Tick
from game.bootstrap import build_initial_state
from game.loop import SimulationEngine
from game.world import World


@dataclass(slots=True)
class MatchCoordinator:
    config: MatchConfig = field(default_factory=MatchConfig)
    initial_state_config: InitialStateConfig = field(default_factory=InitialStateConfig)
    initial_state: dict[str, Any] = field(default_factory=dict)
    current_tick: Tick = Tick(0)
    _pending: dict[int, list[Command]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _issuer_counts: dict[tuple[int, int], int] = field(default_factory=dict)
    _history: dict[int, CommandFrame] = field(default_factory=dict)
    _checksums: dict[int, dict[str, set[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(set))
    )
    _reported_desync_ticks: set[int] = field(default_factory=set)
    _server_checksum_label: str = "__server__"
    _snapshot_tick: Tick = Tick(0)
    _snapshot: dict[str, Any] = field(default_factory=dict)
    _snapshot_engine: SimulationEngine | None = None

    def __post_init__(self) -> None:
        if not self.initial_state:
            self.initial_state = build_initial_state(self.initial_state_config)
        if not self._snapshot:
            self._snapshot = self.initial_state
        if self._snapshot_engine is None:
            self._snapshot_engine = SimulationEngine(
                world=World.from_snapshot(self._snapshot),
                tick=self._snapshot_tick,
            )

    def assign_command(
        self, command: Command, received_at_tick: Tick | None = None
    ) -> Tick:
        base_tick = int(
            self.current_tick if received_at_tick is None else received_at_tick
        )
        target_tick = Tick(base_tick + self.config.command_delay_ticks)
        issuer = int(command.issuer)
        key = (issuer, int(target_tick))
        count = self._issuer_counts.get(key, 0)
        if count >= self.config.max_commands_per_player_per_tick:
            raise ValueError(
                f"too many commands from issuer {command.issuer} for tick {int(target_tick)}"
            )
        self._issuer_counts[key] = count + 1
        self._pending[int(target_tick)].append(command)
        return target_tick

    def build_frame(self) -> CommandFrame:
        commands = tuple(
            canonical_commands(self._pending.pop(int(self.current_tick), ()))
        )
        frame = CommandFrame(tick=self.current_tick, commands=commands)
        if frame.commands:
            self._history[int(frame.tick)] = frame
        self._advance_snapshot_engine(frame)
        self._record_server_checksum()
        self.current_tick = Tick(int(self.current_tick) + 1)
        self._maybe_store_snapshot()
        self._prune_history()
        return frame

    def state_sync_payload(self) -> dict[str, Any]:
        snapshot_tick = int(self._snapshot_tick)
        return {
            "kind": "state_sync",
            "current_tick": int(self.current_tick),
            "snapshot_tick": snapshot_tick,
            "tick_rate": self.config.tick_rate,
            "command_delay_ticks": self.config.command_delay_ticks,
            "checksum_interval_ticks": self.config.checksum_interval_ticks,
            "game_config": game_config_payload(self.initial_state_config),
            "initial_state": self.initial_state,
            "snapshot": self._snapshot,
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
        normalized_checksum = str(checksum)
        self._checksums[int_tick][normalized_checksum].add(str(player_id))
        self._prune_checksums()

        if (
            int_tick in self._reported_desync_ticks
            or len(self._checksums[int_tick]) <= 1
        ):
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

    def timeline_depth(self) -> int:
        if not self._pending:
            return 0
        return max(self._pending) - int(self.current_tick)

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

    def _advance_snapshot_engine(self, frame: CommandFrame) -> None:
        if self._snapshot_engine is None:
            raise RuntimeError("snapshot engine is not initialized")
        self._snapshot_engine.step(frame)

    def _record_server_checksum(self) -> None:
        if self._snapshot_engine is None:
            raise RuntimeError("snapshot engine is not initialized")
        interval = self.config.checksum_interval_ticks
        tick = int(self._snapshot_engine.tick)
        if interval <= 0 or tick <= 0 or tick % interval != 0:
            return
        checksum = checksum_snapshot(tick, self._snapshot_engine.world.to_snapshot())
        self._checksums[tick][checksum].add(self._server_checksum_label)

    def _maybe_store_snapshot(self) -> None:
        if self._snapshot_engine is None:
            raise RuntimeError("snapshot engine is not initialized")
        interval = self.config.snapshot_interval_ticks
        if interval <= 0:
            return
        tick = int(self._snapshot_engine.tick)
        if tick > 0 and tick % interval == 0:
            self._snapshot_tick = Tick(tick)
            self._snapshot = self._snapshot_engine.world.to_snapshot()
