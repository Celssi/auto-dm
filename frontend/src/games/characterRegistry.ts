export type CharacterCreationFlow = 'wizard' | 'immediate';

export interface GameCharacterConfig {
  id: string;
  label: string;
  shortLabel: string;
  creationFlow: CharacterCreationFlow;
  supportsLevelUp: boolean;
}

const GAME_CHARACTER_CONFIG: Record<string, GameCharacterConfig> = {
  dnd5e: {
    id: 'dnd5e',
    label: 'D&D 5e (2024)',
    shortLabel: 'D&D',
    creationFlow: 'wizard',
    supportsLevelUp: true,
  },
  brambletrek: {
    id: 'brambletrek',
    label: 'Brambletrek',
    shortLabel: 'BT',
    creationFlow: 'immediate',
    supportsLevelUp: false,
  },
};

export function getGameCharacterConfig(gameId: string | undefined): GameCharacterConfig {
  return GAME_CHARACTER_CONFIG[gameId ?? 'dnd5e'] ?? GAME_CHARACTER_CONFIG.dnd5e;
}

export function gameShortLabel(gameId: string | undefined): string {
  return getGameCharacterConfig(gameId).shortLabel;
}
