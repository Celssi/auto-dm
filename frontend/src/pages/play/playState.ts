import type {
  ChatResult,
  ChatMessage,
  CombatStateSnapshot,
  JournalEntity,
  PlayerProgress,
  NextAdventure,
  Shortcut,
  Source,
  SpellConfirmation,
} from '../../api/client';
import type { Character } from '../../types';

export type PlayMode = 'freeform' | 'module';

export interface PlayState {
  sessions: { id: string; name: string }[];
  metaLoaded: boolean;
  sessionLoaded: boolean;
  loadError: string;
  characters: { id: string; name: string }[];
  adventures: { id: string; name: string }[];
  sessionId: string;
  messages: ChatMessage[];
  character: Character | null;
  characterId: string;
  characterSummary: Record<string, unknown>;
  input: string;
  loading: boolean;
  bootstrapping: boolean;
  bootstrapError: string;
  beginning: boolean;
  beginError: string;
  shortcuts: Shortcut[];
  oracles: { id: string; label: string }[];
  lonelog: string[];
  sources: Source[];
  includeFaerun: boolean;
  wizardTab: 'continue' | 'new';
  newSession: { character_id: string; adventure_id: string; name: string };
  newCampaign: {
    character_id: string;
    mode: PlayMode;
    theme: string;
    campaign_name: string;
    include_faerun: boolean;
  };
  spellConfirm: SpellConfirmation | null;
  chatError: string;
  journalEntities: JournalEntity[];
  adventureId: string;
  campaignId: string;
  playerProgress: PlayerProgress | null;
  adventureComplete: boolean;
  nextAdventure: NextAdventure | null;
  startingNext: boolean;
  combatState: CombatStateSnapshot | null;
}

export type PlayAction =
  | { type: 'set'; patch: Partial<PlayState> }
  | { type: 'patchNewSession'; patch: Partial<PlayState['newSession']> }
  | { type: 'patchNewCampaign'; patch: Partial<PlayState['newCampaign']> }
  | { type: 'appendMessages'; messages: PlayState['messages'] };

export function createInitialPlayState(sessionId = '', wizardTab: 'continue' | 'new' = 'continue'): PlayState {
  return {
    sessions: [],
    metaLoaded: false,
    sessionLoaded: false,
    loadError: '',
    characters: [],
    adventures: [],
    sessionId,
    messages: [],
    character: null,
    characterId: '',
    characterSummary: {},
    input: '',
    loading: false,
    bootstrapping: false,
    bootstrapError: '',
    beginning: false,
    beginError: '',
    shortcuts: [],
    oracles: [],
    lonelog: [],
    sources: [],
    includeFaerun: false,
    wizardTab,
    newSession: { character_id: '', adventure_id: '', name: '' },
    newCampaign: {
      character_id: '',
      mode: 'freeform',
      theme: '',
      campaign_name: '',
      include_faerun: false,
    },
    spellConfirm: null,
    chatError: '',
    journalEntities: [],
    adventureId: '',
    campaignId: '',
    playerProgress: null,
    adventureComplete: false,
    nextAdventure: null,
    startingNext: false,
    combatState: null,
  };
}

export function playReducer(state: PlayState, action: PlayAction): PlayState {
  switch (action.type) {
    case 'set':
      return { ...state, ...action.patch };
    case 'patchNewSession':
      return { ...state, newSession: { ...state.newSession, ...action.patch } };
    case 'patchNewCampaign':
      return { ...state, newCampaign: { ...state.newCampaign, ...action.patch } };
    case 'appendMessages':
      return { ...state, messages: [...state.messages, ...action.messages] };
    default:
      return state;
  }
}

export type { ChatResult };
