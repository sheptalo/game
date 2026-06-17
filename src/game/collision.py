from typing import Literal

from game.components.base import Collision, Position

Axis = Literal["x", "y"]

# Precomputed AABB for an obstacle: (entity_id, left, right, bottom, top)
ObstacleBox = tuple[int, int, int, int, int]


def aabb(position: Position, collision: Collision) -> tuple[int, int, int, int]:
    half_w = collision.width // 2
    half_h = collision.height // 2
    return (
        position.x - half_w,
        position.x + half_w,
        position.y - half_h,
        position.y + half_h,
    )


def x_overlap(left_a: int, right_a: int, left_b: int, right_b: int) -> bool:
    return left_a < right_b and left_b < right_a


def y_overlap(bottom_a: int, top_a: int, bottom_b: int, top_b: int) -> bool:
    return bottom_a < top_b and bottom_b < top_a


def x_touch(
    left_a: int,
    right_a: int,
    left_b: int,
    right_b: int,
    tolerance: int = 1,
) -> bool:
    return left_a <= right_b + tolerance and left_b - tolerance <= right_a


def y_touch(
    bottom_a: int,
    top_a: int,
    bottom_b: int,
    top_b: int,
    tolerance: int = 1,
) -> bool:
    return bottom_a <= top_b + tolerance and bottom_b - tolerance <= top_a


def aabb_touch(
    position_a: Position,
    collision_a: Collision,
    position_b: Position,
    collision_b: Collision,
    tolerance: int = 1,
) -> bool:
    left_a, right_a, bottom_a, top_a = aabb(position_a, collision_a)
    left_b, right_b, bottom_b, top_b = aabb(position_b, collision_b)
    return x_touch(left_a, right_a, left_b, right_b, tolerance) and y_touch(bottom_a, top_a, bottom_b, top_b, tolerance)


def is_grounded(
    entity_id: int,
    pos_x: int,
    pos_y: int,
    col_w: int,
    col_h: int,
    obstacles: list[ObstacleBox],
) -> bool:
    half_w = col_w // 2
    half_h = col_h // 2
    left = pos_x - half_w
    right = pos_x + half_w
    bottom = pos_y - half_h
    for other_id, o_left, o_right, _o_bottom, o_top in obstacles:
        if other_id == entity_id:
            continue
        if not x_overlap(left, right, o_left, o_right):
            continue
        if bottom - 1 <= o_top <= bottom + 1:
            return True
    return False


def resolve_axis( # noqa: PLR0912, C901
    pos_x: int,
    pos_y: int,
    col_w: int,
    col_h: int,
    obstacles: list[ObstacleBox],
    entity_id: int,
    axis: Axis,
    delta: int,
) -> int:
    if delta == 0:
        return pos_x if axis == "x" else pos_y

    half_w = col_w // 2
    half_h = col_h // 2

    if axis == "x":
        target = pos_x + delta
        left = target - half_w
        right = target + half_w
        bottom = pos_y - half_h
        top = pos_y + half_h
        for other_id, o_left, o_right, o_bottom, o_top in obstacles:
            if other_id == entity_id:
                continue
            if not y_overlap(bottom, top, o_bottom, o_top):
                continue
            if not x_overlap(left, right, o_left, o_right):
                continue
            target = min(target, o_left - half_w) if delta > 0 else max(target, o_right + half_w)
            left = target - half_w
            right = target + half_w
        return target

    target = pos_y + delta
    current_bottom = pos_y - half_h
    left = pos_x - half_w
    right = pos_x + half_w
    bottom = target - half_h
    target_bottom = bottom

    for other_id, o_left, o_right, o_bottom, o_top in obstacles:
        if other_id == entity_id:
            continue
        if not x_overlap(left, right, o_left, o_right):
            continue
        if delta > 0:
            if o_bottom <= pos_y:
                continue
            ceiling_center_y = o_bottom - half_h
            target = min(target, ceiling_center_y)
        else:
            if o_top > current_bottom + 1:
                continue
            if target_bottom <= o_top + 1:
                platform_land_y = o_top + half_h
                if platform_land_y > target:
                    target = platform_land_y
                    target_bottom = target - half_h
    return target
