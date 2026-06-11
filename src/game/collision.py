from typing import Literal

from game.components.base import Collision, Position

Axis = Literal["x", "y"]


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


def is_grounded(
    entity_id: int,
    position: Position,
    collision: Collision,
    obstacles: list[tuple[int, Position, Collision]],
) -> bool:
    left, right, bottom, _top = aabb(position, collision)
    for other_id, other_pos, other_col in obstacles:
        if other_id == entity_id:
            continue
        o_left, o_right, _o_bottom, o_top = aabb(other_pos, other_col)
        if not x_overlap(left, right, o_left, o_right):
            continue
        if bottom - 1 <= o_top <= bottom + 1:
            return True
    return False


def resolve_axis(
    position: Position,
    collision: Collision,
    obstacles: list[tuple[int, Position, Collision]],
    entity_id: int,
    axis: Axis,
    delta: int,
) -> int:
    if delta == 0:
        return position.x if axis == "x" else position.y

    half_w = collision.width // 2
    half_h = collision.height // 2

    if axis == "x":
        target = position.x + delta
        probe = Position(target, position.y)
        left, right, bottom, top = aabb(probe, collision)
        for other_id, other_pos, other_col in obstacles:
            if other_id == entity_id:
                continue
            o_left, o_right, o_bottom, o_top = aabb(other_pos, other_col)
            if not y_overlap(bottom, top, o_bottom, o_top):
                continue
            if not x_overlap(left, right, o_left, o_right):
                continue
            if delta > 0:
                target = min(target, o_left - half_w)
            else:
                target = max(target, o_right + half_w)
            probe = Position(target, position.y)
            left, right, bottom, top = aabb(probe, collision)
        return target

    target = position.y + delta
    current_bottom = position.y - half_h
    probe = Position(position.x, target)
    left, right, bottom, top = aabb(probe, collision)
    target_bottom = bottom

    for other_id, other_pos, other_col in obstacles:
        if other_id == entity_id:
            continue
        o_left, o_right, o_bottom, o_top = aabb(other_pos, other_col)
        if not x_overlap(left, right, o_left, o_right):
            continue
        if delta > 0:
            if o_bottom <= position.y:
                continue
            ceiling_center_y = o_bottom - half_h
            if ceiling_center_y < target:
                target = ceiling_center_y
                probe = Position(position.x, target)
                left, right, bottom, top = aabb(probe, collision)
        else:
            if o_top > current_bottom + 1:
                continue
            if target_bottom <= o_top + 1:
                platform_land_y = o_top + half_h
                if platform_land_y > target:
                    target = platform_land_y
                    probe = Position(position.x, target)
                    _, _, target_bottom, _ = aabb(probe, collision)
    return target
