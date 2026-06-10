from game.systems import movement

SYSTEMS = frozenset((movement.MovementProcessor(),))


__all__ = ["SYSTEMS"]
