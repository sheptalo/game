export function teleport(snapshot, unitId) {
  const entity = snapshot.entities.find((candidate) => candidate.id === unitId);
  if (!entity?.Position) return;
  entity.Position.x = 0;
  entity.Position.y = 0;
}
