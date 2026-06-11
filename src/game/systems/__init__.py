from game.systems import movement, trigger

SYSTEMS = (movement.MovementProcessor(), trigger.TriggerSystem())


__all__ = ["SYSTEMS"]
