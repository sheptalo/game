import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.types import EntityId


@pytest.fixture
def mock_world(monkeypatch):
    import server.match as m
    monkeypatch.setattr(m.world, "init", lambda config: None)
    monkeypatch.setattr(m.world, "player_entities", lambda: [EntityId(6), EntityId(7)])
    monkeypatch.setattr(m.world, "snapshot", dict)
