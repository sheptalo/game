from dataclasses import fields
from typing import Any

import esper

from game.components import COMPONENTS
from game.components.base import OwnedBy


def entity_to_record(entity_id: int) -> dict[str, Any]:
    record: dict[str, Any] = {"id": entity_id}
    for component_type in COMPONENTS:
        if not esper.has_component(entity_id, component_type):
            continue
        component = esper.component_for_entity(entity_id, component_type)
        payload = {
            field.name: getattr(component, field.name)
            for field in fields(component_type)
        }
        if component_type is OwnedBy:
            payload["owner"] = int(payload["owner"])
        record[component_type.__name__] = payload
    return record
