export const DEFAULT_GAME_ID = 'dnd5e';

export const GAMES = [{ id: 'dnd5e', label: 'D&D 5e (2024)' }] as const;

export type GameId = (typeof GAMES)[number]['id'];

export function gameLabel(gameId: string | undefined): string {
  return GAMES.find((g) => g.id === gameId)?.label ?? gameId ?? DEFAULT_GAME_ID;
}
