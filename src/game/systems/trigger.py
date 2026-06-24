import esper

from game.collision import aabb_touch
from game.components.base import Collision, Position, Trigger, TriggerOverlap


class TriggerSystem(esper.Processor):
    def process(self) -> None:
        triggers = sorted(
            esper.get_components(Position, Collision, Trigger),
            key=lambda item: item[0],
        )
        trigger_map: dict[int, Trigger] = {eid: t for eid, (_, _, t) in triggers}
        units = sorted(
            esper.get_components(Position, Collision, TriggerOverlap),
            key=lambda item: item[0],
        )
        for unit_id, (u_pos, u_col, overlap) in units:
            previous = set(overlap.inside)
            current: set[int] = set()
            for trig_id, (t_pos, t_col, _) in triggers:
                if not aabb_touch(u_pos, u_col, t_pos, t_col):
                    continue
                current.add(trig_id)
            for trig_id in sorted(current - previous):
                trigger = trigger_map[trig_id]
                esper.dispatch_event(trigger.on_enter, unit_id)
            for trig_id in sorted(previous - current):
                trigger = trigger_map[trig_id]
                esper.dispatch_event(trigger.on_exit, unit_id)
            overlap.inside = sorted(current)
