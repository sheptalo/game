from game.components.base import Collision, Position


def aabb(position: Position, collision: Collision) -> tuple[int, int, int, int]:
    half_w = collision.width // 2
    half_h = collision.height // 2
    return (
        position.x - half_w,
        position.x + half_w,
        position.y - half_h,
        position.y + half_h,
    )


def x_overlap(
    left_a: int, right_a: int, left_b: int, right_b: int
) -> bool:
    return left_a < right_b and left_b < right_a


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


def resolve_jump_y(
    position: Position,
    collision: Collision,
    obstacles: list[tuple[int, Position, Collision]],
    entity_id: int,
    jump_height: int,
) -> int:
    target_y = position.y + jump_height
    _left, _right, _bottom, top = aabb(
        Position(position.x, target_y), collision
    )
    half_h = collision.height // 2

    for other_id, other_pos, other_col in obstacles:
        if other_id == entity_id:
            continue
        o_left, o_right, o_bottom, _o_top = aabb(other_pos, other_col)
        if not x_overlap(_left, _right, o_left, o_right):
            continue
        if o_bottom <= position.y:
            continue
        ceiling_center_y = o_bottom - half_h
        if ceiling_center_y < target_y:
            target_y = ceiling_center_y
    return target_y


def resolve_fall_y(
    position: Position,
    collision: Collision,
    obstacles: list[tuple[int, Position, Collision]],
    entity_id: int,
    fall_speed: int,
) -> int:
    half_h = collision.height // 2
    left, right, bottom, _top = aabb(position, collision)
    target_y = position.y - fall_speed
    target_bottom = bottom - fall_speed
    land_y = target_y

    for other_id, other_pos, other_col in obstacles:
        if other_id == entity_id:
            continue
        o_left, o_right, _o_bottom, o_top = aabb(other_pos, other_col)
        if not x_overlap(left, right, o_left, o_right):
            continue
        if o_top > bottom + 1:
            continue
        if target_bottom <= o_top + 1:
            platform_land_y = o_top + half_h
            if platform_land_y > land_y:
                land_y = platform_land_y
    return land_y
