export type ExtraToolTab = 'journey' | 'deck' | 'combat';

export interface GamePlayConfig {
  usesDiceModal: boolean;
  usesOracles: boolean;
  usesCombatPanel: boolean;
  campaignThemeRequired: boolean;
  /** D&D-style AI campaign generation (story arc + adventure sequence). */
  usesAiCampaignGeneration: boolean;
  showFaerunToggle: boolean;
  extraToolTabs: ExtraToolTab[];
  shortcutGroups?: boolean;
}

const GAME_PLAY_CONFIG: Record<string, GamePlayConfig> = {
  dnd5e: {
    usesDiceModal: true,
    usesOracles: true,
    usesCombatPanel: true,
    campaignThemeRequired: true,
    usesAiCampaignGeneration: true,
    showFaerunToggle: true,
    extraToolTabs: [],
    shortcutGroups: false,
  },
  brambletrek: {
    usesDiceModal: false,
    usesOracles: false,
    usesCombatPanel: false,
    campaignThemeRequired: false,
    usesAiCampaignGeneration: false,
    showFaerunToggle: false,
    extraToolTabs: ['journey', 'deck'],
    shortcutGroups: true,
  },
};

export function getGamePlayConfig(gameId: string | undefined): GamePlayConfig {
  return GAME_PLAY_CONFIG[gameId ?? 'dnd5e'] ?? GAME_PLAY_CONFIG.dnd5e;
}
