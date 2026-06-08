from __future__ import annotations


from rts_engine.simulation.world import World


def movement_system(world: World) -> None:
    for index in world.units.sorted_indices():
        current_x = world.units.x[index]
        current_y = world.units.y[index]
        target_x = world.units.target_x[index]
        target_y = world.units.target_y[index]
        dx = target_x - current_x
        dy = target_y - current_y
        if dx == 0 and dy == 0:
            continue

        step = world.units.speed[index]
        distance_sq = dx * dx + dy * dy
        if distance_sq <= step * step:
            world.units.x[index] = target_x
            world.units.y[index] = target_y
            continue

        # Integer-only approximation: advance along the dominant axis.
        dominant = max(abs(dx), abs(dy))
        world.units.x[index] += _trunc_div(dx * step, dominant)
        world.units.y[index] += _trunc_div(dy * step, dominant)


def _trunc_div(numerator: int, denominator: int) -> int:
    if numerator < 0:
        return -((-numerator) // denominator)
    return numerator // denominator
