import pytest

from core.commands import Command, CommandFrame, CommandType
from core.types import EntityId, Tick
from game.protocol import command_from_client_wire, command_to_client_wire
from network.protocol import decode_command_frame, encode_command_frame

pytest.importorskip("msgpack")


def test_command_frame_round_trip() -> None:
    frame = CommandFrame(
        tick=Tick(7),
        commands=(Command(type=CommandType.MOVE, issuer=EntityId(1), sequence=42),),
    )

    assert decode_command_frame(encode_command_frame(frame)) == frame


def test_legacy_client_wire_maps_player_slot_to_issuer() -> None:
    command = command_from_client_wire(
        {
            "type": "MOVE",
            "player_id": "p7",
            "sequence": 3,
            "units": [108],
            "x": 5000,
            "y": 6000,
        }
    )
    assert command.issuer == EntityId(7)
    assert command.targets == (EntityId(108),)


def test_command_to_client_wire_keeps_legacy_fields() -> None:
    wire = command_to_client_wire(
        Command(
            type=CommandType.MOVE,
            issuer=EntityId(2),
            sequence=1,
            targets=(EntityId(103),),
            x=1000,
            y=2000,
        )
    )
    assert wire["player_id"] == "p2"
    assert wire["units"] == [103]
