from __future__ import annotations

from dataclasses import fields
from typing import Any

import esper

from core.types import EntityId
from game.components import Movement, OwnedBy, Position, Resources

GAME_COMPONENTS = (Resources, OwnedBy, Position, Movement)
COMPONENT_BY_NAME = {component.__name__: component for component in GAME_COMPONENTS}


def _component_payload(component_type: type, component: object) -> dict[str, Any]:
    payload = {field.name: getattr(component, field.name) for field in fields(component_type)}
    if component_type is OwnedBy:
        payload["owner"] = int(payload["owner"])
    return payload


def entity_to_record(entity_id: int) -> dict[str, Any]:
    record: dict[str, Any] = {"id": entity_id}
    for component_type in GAME_COMPONENTS:
        if not esper.has_component(entity_id, component_type):
            continue
        component = esper.component_for_entity(entity_id, component_type)
        record[component_type.__name__] = _component_payload(component_type, component)
    return record


def apply_record(world: Any, record: dict[str, Any]) -> int:
    entity_id = int(record["id"])
    entity = world.create(entity_id)
    for name, payload in record.items():
        if name == "id":
            continue
        component_type = COMPONENT_BY_NAME[name]
        if component_type is OwnedBy:
            esper.add_component(entity, OwnedBy(EntityId(int(payload["owner"]))))
        else:
            esper.add_component(entity, component_type(**payload))
    return entity
