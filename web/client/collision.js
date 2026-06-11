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

export function resolveJumpY(position, collision, obstacles, entityId, jumpHeight) {
  let targetY = position.y + jumpHeight;
  const halfH = Math.floor(collision.height / 2);
  const atTarget = aabb({ x: position.x, y: targetY }, collision);

  for (const [otherId, otherPos, otherCol] of obstacles) {
    if (otherId === entityId) continue;
    const other = aabb(otherPos, otherCol);
    if (!xOverlap(atTarget.left, atTarget.right, other.left, other.right)) continue;
    if (other.bottom <= position.y) continue;
    const ceilingCenterY = other.bottom - halfH;
    if (ceilingCenterY < targetY) targetY = ceilingCenterY;
  }
  return targetY;
}

export function resolveFallY(position, collision, obstacles, entityId, fallSpeed) {
  const halfH = Math.floor(collision.height / 2);
  const { left, right, bottom } = aabb(position, collision);
  let landY = position.y - fallSpeed;
  const targetBottom = bottom - fallSpeed;

  for (const [otherId, otherPos, otherCol] of obstacles) {
    if (otherId === entityId) continue;
    const other = aabb(otherPos, otherCol);
    if (!xOverlap(left, right, other.left, other.right)) continue;
    if (other.top > bottom + 1) continue;
    if (targetBottom <= other.top + 1) {
      const platformLandY = other.top + halfH;
      if (platformLandY > landY) landY = platformLandY;
    }
  }
  return landY;
}

export function collectObstacles(snapshot) {
  return sortedEntities(snapshot)
    .filter((entity) => entity.Position && entity.Collision)
    .map((entity) => [entity.id, entity.Position, entity.Collision]);
}

function sortedEntities(snapshot) {
  return [...snapshot.entities].sort((a, b) => a.id - b.id);
}
