import pytest

from config import InitialStateConfig
from core.types import EntityId
from server.match import MatchCoordinator


def test_token_count_mismatch_raises(mock_world):
    config = InitialStateConfig(player_count=2, player_tokens=("only-one",))
    with pytest.raises(ValueError, match="player_tokens"):
        MatchCoordinator(game_config=config)


def test_no_tokens_skips_auth(mock_world):
    config = InitialStateConfig(player_count=2, player_tokens=())
    coordinator = MatchCoordinator(game_config=config)
    assert coordinator.authenticate("any") is None
