from typing import TYPE_CHECKING

from game.systems import movement, trigger

if TYPE_CHECKING:
    from config import InitialStateConfig


def make_systems(config: InitialStateConfig):
    return (movement.MovementProcessor(config), trigger.TriggerSystem())


__all__ = ["make_systems"]
