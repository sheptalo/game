import { DEFAULT_GAME_CONFIG } from "../constants.js";

export function spawn(snapshot, unitId) {
  const entity = snapshot.entities.find((candidate) => candidate.id === unitId);
  if (!entity?.Position) return;
  entity.Position.x = 5000;
  entity.Position.y = 5000;
}
