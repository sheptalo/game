export function aabb(position, collision) {
  const halfW = Math.floor(collision.width / 2);
  const halfH = Math.floor(collision.height / 2);
  return {
    left: position.x - halfW,
    right: position.x + halfW,
    bottom: position.y - halfH,
    top: position.y + halfH,
  };
}

export function xOverlap(leftA, rightA, leftB, rightB) {
  return leftA < rightB && leftB < rightA;
}

export function yOverlap(bottomA, topA, bottomB, topB) {
  return bottomA < topB && bottomB < topA;
}

export function isGrounded(entityId, position, collision, obstacles) {
  const { left, right, bottom } = aabb(position, collision);
  for (const [otherId, otherPos, otherCol] of obstacles) {
    if (otherId === entityId) continue;
    const other = aabb(otherPos, otherCol);
    if (!xOverlap(left, right, other.left, other.right)) continue;
    if (bottom - 1 <= other.top && other.top <= bottom + 1) return true;
  }
  return false;
}

export function resolveAxis(
  position,
  collision,
  obstacles,
  entityId,
  axis,
  delta,
) {
  if (delta === 0) {
    return axis === "x" ? position.x : position.y;
  }

  const halfW = Math.floor(collision.width / 2);
  const halfH = Math.floor(collision.height / 2);

  if (axis === "x") {
    let target = position.x + delta;
    let probe = { x: target, y: position.y };
    let box = aabb(probe, collision);

    for (const [otherId, otherPos, otherCol] of obstacles) {
      if (otherId === entityId) continue;
      const other = aabb(otherPos, otherCol);
      if (!yOverlap(box.bottom, box.top, other.bottom, other.top)) continue;
      if (!xOverlap(box.left, box.right, other.left, other.right)) continue;
      if (delta > 0) {
        target = Math.min(target, other.left - halfW);
      } else {
        target = Math.max(target, other.right + halfW);
      }
      probe = { x: target, y: position.y };
      box = aabb(probe, collision);
    }
    return target;
  }

  let target = position.y + delta;
  const currentBottom = position.y - halfH;
  let probe = { x: position.x, y: target };
  let box = aabb(probe, collision);
  let targetBottom = box.bottom;

  for (const [otherId, otherPos, otherCol] of obstacles) {
    if (otherId === entityId) continue;
    const other = aabb(otherPos, otherCol);
    if (!xOverlap(box.left, box.right, other.left, other.right)) continue;
    if (delta > 0) {
      if (other.bottom <= position.y) continue;
      const ceilingCenterY = other.bottom - halfH;
      if (ceilingCenterY < target) {
        target = ceilingCenterY;
        probe = { x: position.x, y: target };
        box = aabb(probe, collision);
      }
    } else {
      if (other.top > currentBottom + 1) continue;
      if (targetBottom <= other.top + 1) {
        const platformLandY = other.top + halfH;
        if (platformLandY > target) {
          target = platformLandY;
          probe = { x: position.x, y: target };
          targetBottom = aabb(probe, collision).bottom;
        }
      }
    }
  }
  return target;
}

export function collectObstacles(snapshot) {
  return sortedEntities(snapshot)
    .filter((entity) => entity.Position && entity.Collision)
    .map((entity) => [entity.id, entity.Position, entity.Collision]);
}

function sortedEntities(snapshot) {
  return [...snapshot.entities].sort((a, b) => a.id - b.id);
}
