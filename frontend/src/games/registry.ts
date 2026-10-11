export const DEFAULT_GAME_ID = 'dnd5e';

export const GAMES = [
  {
    id: 'dnd5e',
    label: 'D&D 5e (2024)',
    description: 'Solo play with Claude as your Dungeon Master: rules lookup, oracles, and a living journal.',
    accent: '#d4af37',
    accentDim: '#a8882a',
  },
  {
    id: 'brambletrek',
    label: 'Brambletrek',
    description: 'Card-driven solo journeys for a Gnawborn. Draw, travel, and journal what happens.',
    accent: '#6b8f4e',
    accentDim: '#55723d',
  },
] as const;

export type GameId = (typeof GAMES)[number]['id'];
export type GameDefinition = (typeof GAMES)[number];

export { getGameCharacterConfig, gameShortLabel } from './characterRegistry';
export type { GameCharacterConfig, CharacterCreationFlow } from './characterRegistry';

export function isGameId(value: string | undefined): value is GameId {
  return GAMES.some((g) => g.id === value);
}

export function getGame(gameId: string | undefined): GameDefinition {
  return GAMES.find((g) => g.id === gameId) ?? GAMES[0];
}

export function gameLabel(gameId: string | undefined): string {
  return getGame(gameId).label;
}
