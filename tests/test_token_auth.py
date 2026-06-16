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


def test_authenticate_known_tokens(mock_world):
    config = InitialStateConfig(player_count=2, player_tokens=("tok1", "tok2"))
    coordinator = MatchCoordinator(game_config=config)
    assert coordinator.authenticate("tok1") == EntityId(6)
    assert coordinator.authenticate("tok2") == EntityId(7)


def test_authenticate_unknown_token_returns_none(mock_world):
    config = InitialStateConfig(player_count=2, player_tokens=("tok1", "tok2"))
    coordinator = MatchCoordinator(game_config=config)
    assert coordinator.authenticate("bad") is None


def test_reconnect_returns_same_player_id(mock_world):
    config = InitialStateConfig(player_count=2, player_tokens=("tok1", "tok2"))
    coordinator = MatchCoordinator(game_config=config)
    assert coordinator.authenticate("tok1") == coordinator.authenticate("tok1")


def test_two_players_get_different_ids(mock_world):
    config = InitialStateConfig(player_count=2, player_tokens=("tok1", "tok2"))
    coordinator = MatchCoordinator(game_config=config)
    assert coordinator.authenticate("tok1") != coordinator.authenticate("tok2")
