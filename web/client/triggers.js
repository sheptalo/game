import { aabbTouch } from "./collision.js";
import { spawn } from "./subscribers/spawn.js";
import { teleport } from "./subscribers/teleport.js";

const EVENT_HANDLERS = {
  teleport,
  spawn,
};

function sortedEntities(snapshot) {
  return [...snapshot.entities].sort((a, b) => a.id - b.id);
}

function collectTriggers(snapshot) {
  return sortedEntities(snapshot)
    .filter((entity) => entity.Position && entity.Collision && entity.Trigger)
    .map((entity) => [entity.id, entity.Position, entity.Collision, entity.Trigger]);
}

function collectTriggerUnits(snapshot) {
  return sortedEntities(snapshot).filter(
    (entity) =>
      entity.Position &&
      entity.Collision &&
      entity.OwnedBy &&
      entity.TriggerOverlap,
  );
}

function dispatchEvent(name, snapshot, unitId, events) {
  if (!name) return;
  const handler = EVENT_HANDLERS[name];
  if (handler) {
    handler(snapshot, unitId);
  }
  events.push({
    kind: "trigger_event",
    name,
    entity_id: unitId,
  });
}

export function resetTriggerState(state) {
  state.triggerEvents = [];
}

export function processTriggers(state) {
  const triggers = collectTriggers(state.snapshot);
  const units = collectTriggerUnits(state.snapshot);
  if (!state.triggerEvents) {
    state.triggerEvents = [];
  }

  for (const entity of units) {
    const overlap = entity.TriggerOverlap;
    const previous = new Set(overlap.inside ?? []);
    const current = new Set();

    for (const [triggerId, triggerPos, triggerCol] of triggers) {
      if (
        aabbTouch(
          entity.Position,
          entity.Collision,
          triggerPos,
          triggerCol,
        )
      ) {
        current.add(triggerId);
      }
    }

    for (const triggerId of [...current].sort((a, b) => a - b)) {
      if (previous.has(triggerId)) continue;
      const trigger = triggers.find(([id]) => id === triggerId)?.[3];
      if (!trigger?.on_enter) continue;
      dispatchEvent(trigger.on_enter, state.snapshot, entity.id, state.triggerEvents);
    }

    for (const triggerId of [...previous].sort((a, b) => a - b)) {
      if (current.has(triggerId)) continue;
      const trigger = triggers.find(([id]) => id === triggerId)?.[3];
      if (!trigger?.on_exit) continue;
      dispatchEvent(trigger.on_exit, state.snapshot, entity.id, state.triggerEvents);
    }

    overlap.inside = [...current].sort((a, b) => a - b);
  }
}

export function drainTriggerEvents(state) {
  const events = state.triggerEvents ?? [];
  state.triggerEvents = [];
  return events;
}
