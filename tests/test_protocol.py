import pytest

from rts_engine.core.commands import Command, CommandFrame, CommandType
from rts_engine.core.types import PlayerId, Tick
from rts_engine.network.protocol import decode_command_frame, encode_command_frame


pytest.importorskip("msgpack")


def test_command_frame_round_trip() -> None:
    frame = CommandFrame(
        tick=Tick(7),
        commands=(
            Command(type=CommandType.MOVE, player_id=PlayerId("p1"), sequence=42),
        ),
    )

    decoded = decode_command_frame(encode_command_frame(frame))

    assert decoded == frame
