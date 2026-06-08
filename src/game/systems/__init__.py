from game.systems.command import CommandSystem
from game.systems.movement import MovementSystem

default_systems = (MovementSystem,)

__all__ = [
    "CommandSystem",
    "MovementSystem",
    "default_systems",
]
