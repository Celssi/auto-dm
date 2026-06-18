import type { ChatResult, JournalEntity, Shortcut, Source, SpellConfirmation } from '../../api/client';
import type { Character } from '../../types';

export type PlayMode = 'freeform' | 'module';

export interface PlayState {
  sessions: { id: string; name: string }[];
  metaLoaded: boolean;
  sessionLoaded: boolean;
  characters: { id: string; name: string }[];
  adventures: { id: string; name: string }[];
  sessionId: string;
  messages: Array<{ role: string; content: string }>;
  character: Character | null;
  characterId: string;
  characterSummary: Record<string, unknown>;
  input: string;
  loading: boolean;
  bootstrapping: boolean;
  bootstrapError: string;
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
