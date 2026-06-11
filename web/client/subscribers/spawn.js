import { DEFAULT_GAME_CONFIG } from "../constants.js";

export function spawn(snapshot, unitId) {
  const entity = snapshot.entities.find((candidate) => candidate.id === unitId);
  if (!entity?.Position) return;
  entity.Position.x = DEFAULT_GAME_CONFIG.spawn_start_x;
  entity.Position.y = DEFAULT_GAME_CONFIG.spawn_start_y;
}
