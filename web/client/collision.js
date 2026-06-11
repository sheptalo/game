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

export function xTouch(leftA, rightA, leftB, rightB, tolerance = 1) {
  return leftA <= rightB + tolerance && leftB - tolerance <= rightA;
}

export function yTouch(bottomA, topA, bottomB, topB, tolerance = 1) {
  return bottomA <= topB + tolerance && bottomB - tolerance <= topA;
}

export function aabbTouch(positionA, collisionA, positionB, collisionB, tolerance = 1) {
  const boxA = aabb(positionA, collisionA);
  const boxB = aabb(positionB, collisionB);
  return (
    xTouch(boxA.left, boxA.right, boxB.left, boxB.right, tolerance) &&
    yTouch(boxA.bottom, boxA.top, boxB.bottom, boxB.top, tolerance)
  );
}

// obstacles: [entityId, left, right, bottom, top] — snapshotted at tick start
export function isGrounded(entityId, position, collision, obstacles) {
  const halfW = Math.floor(collision.width / 2);
  const halfH = Math.floor(collision.height / 2);
  const left = position.x - halfW;
  const right = position.x + halfW;
  const bottom = position.y - halfH;
  for (const [otherId, oLeft, oRight, , oTop] of obstacles) {
    if (otherId === entityId) continue;
    if (!xOverlap(left, right, oLeft, oRight)) continue;
    if (bottom - 1 <= oTop && oTop <= bottom + 1) return true;
  }
  return false;
}

export function resolveAxis(position, collision, obstacles, entityId, axis, delta) {
  if (delta === 0) {
    return axis === "x" ? position.x : position.y;
  }

  const halfW = Math.floor(collision.width / 2);
  const halfH = Math.floor(collision.height / 2);

  if (axis === "x") {
    let target = position.x + delta;
    let left = target - halfW;
    let right = target + halfW;
    const bottom = position.y - halfH;
    const top = position.y + halfH;

    for (const [otherId, oLeft, oRight, oBottom, oTop] of obstacles) {
      if (otherId === entityId) continue;
      if (!yOverlap(bottom, top, oBottom, oTop)) continue;
      if (!xOverlap(left, right, oLeft, oRight)) continue;
      target = delta > 0 ? Math.min(target, oLeft - halfW) : Math.max(target, oRight + halfW);
      left = target - halfW;
      right = target + halfW;
    }
    return target;
  }

  let target = position.y + delta;
  const currentBottom = position.y - halfH;
  const left = position.x - halfW;
  const right = position.x + halfW;
  let targetBottom = target - halfH;

  for (const [otherId, oLeft, oRight, oBottom, oTop] of obstacles) {
    if (otherId === entityId) continue;
    if (!xOverlap(left, right, oLeft, oRight)) continue;
    if (delta > 0) {
      if (oBottom <= position.y) continue;
      const ceilingCenterY = oBottom - halfH;
      if (ceilingCenterY < target) {
        target = ceilingCenterY;
      }
    } else {
      if (oTop > currentBottom + 1) continue;
      if (targetBottom <= oTop + 1) {
        const platformLandY = oTop + halfH;
        if (platformLandY > target) {
          target = platformLandY;
          targetBottom = target - halfH;
        }
      }
    }
  }
  return target;
}

// Returns [entityId, left, right, bottom, top] — positions snapshotted at call time
export function collectObstacles(snapshot) {
  return sortedEntities(snapshot)
    .filter((entity) => entity.Position && entity.Collision && !entity.Trigger)
    .map((entity) => {
      const halfW = Math.floor(entity.Collision.width / 2);
      const halfH = Math.floor(entity.Collision.height / 2);
      return [
        entity.id,
        entity.Position.x - halfW,
        entity.Position.x + halfW,
        entity.Position.y - halfH,
        entity.Position.y + halfH,
      ];
    });
}

function sortedEntities(snapshot) {
  return [...snapshot.entities].sort((a, b) => a.id - b.id);
}
