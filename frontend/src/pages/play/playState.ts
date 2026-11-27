import type {
  AuditEvent,
  ChatResult,
  ChatMessage,
  CombatStateSnapshot,
  JournalEntity,
  SessionRecap,
  SessionWorld,
  PlayerProgress,
  NextAdventure,
  Shortcut,
  Source,
  SpellConfirmation,
  ReactionPrompt,
  StoryMode,
  CardSource,
} from '../../api/client';
import type { Character, DragonkeepState, PendingJourney } from '../../types';

export type PlayMode = 'freeform' | 'module';
export type Advantage = 'normal' | 'advantage' | 'disadvantage';
export type { StoryMode, CardSource };

export interface SpellCastModalState {
  spellName: string;
  slotLevel: number;
  freeUse: boolean;
  ritual: boolean;
  submitting: boolean;
}

export interface DiceModalState {
  shortcutId: string;
  label: string;
  ability: string;
  advantage: Advantage;
  proficient: boolean;
  modifier: number;
  diceCount: number;
  hasModifier: boolean;
  showAbilityPicker: boolean;
  showProficiency: boolean;
  mode: 'manual' | 'auto';
  manualValues: (number | null)[];
  autoResult: number[] | null;
  rolling: boolean;
  submitting: boolean;
}

export interface PlayState {
  sessions: { id: string; name: string; character_id?: string; archived?: boolean; created_at?: string }[];
  metaLoaded: boolean;
  sessionLoaded: boolean;
  loadError: string;
  characters: { id: string; name: string; game_id?: string }[];
  adventures: { id: string; name: string; game_id?: string }[];
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
  oracles: { id: string; label: string; help?: string }[];
  lonelog: string[];
  auditEvents: AuditEvent[];
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
    active_adventure: string;
  };
  spellConfirm: SpellConfirmation | null;
  reactionPrompt: ReactionPrompt | null;
  chatError: string;
  journalEntities: JournalEntity[];
  recap: SessionRecap | null;
  recapLoading: boolean;
  world: SessionWorld | null;
  /** True until the NPC/location fetch for the current session has resolved. */
  worldLoading: boolean;
  worldError: boolean;
  adventureId: string;
  campaignId: string;
  playerProgress: PlayerProgress | null;
  adventureComplete: boolean;
  nextAdventure: NextAdventure | null;
  startingNext: boolean;
  combatState: CombatStateSnapshot | null;
  brambletrekCombat: import('../../types').BrambletrekCombatState | null;
  diceModal: DiceModalState | null;
  spellCastModal: SpellCastModalState | null;
  sheetUpdating: boolean;
  queuedCount: number;
  pendingJourney: PendingJourney | null;
  dragonkeep: DragonkeepState | null;
  storyMode: StoryMode;
  cardSource: CardSource;
}

export type PlayAction =
  | { type: 'set'; patch: Partial<PlayState> }
  | { type: 'patchNewSession'; patch: Partial<PlayState['newSession']> }
  | { type: 'patchNewCampaign'; patch: Partial<PlayState['newCampaign']> }
  | { type: 'appendMessages'; messages: PlayState['messages'] }
  | { type: 'appendAssistantDelta'; delta: string }
  | { type: 'replaceLastAssistant'; content: string };

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
    auditEvents: [],
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
      active_adventure: '',
    },
    spellConfirm: null,
    reactionPrompt: null,
    chatError: '',
    journalEntities: [],
    recap: null,
    recapLoading: false,
    world: null,
    worldLoading: true,
    worldError: false,
    adventureId: '',
    campaignId: '',
    playerProgress: null,
    adventureComplete: false,
    nextAdventure: null,
    startingNext: false,
    combatState: null,
    brambletrekCombat: null,
    diceModal: null,
    spellCastModal: null,
    sheetUpdating: false,
    queuedCount: 0,
    pendingJourney: null,
    dragonkeep: null,
    storyMode: 'player',
    cardSource: 'virtual',
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
    case 'appendAssistantDelta': {
      const messages = [...state.messages];
      for (let i = messages.length - 1; i >= 0; i -= 1) {
        if (messages[i].role === 'assistant') {
          messages[i] = { ...messages[i], content: `${messages[i].content}${action.delta}` };
          break;
        }
      }
      return { ...state, messages };
    }
    case 'replaceLastAssistant': {
      const messages = [...state.messages];
      for (let i = messages.length - 1; i >= 0; i -= 1) {
        if (messages[i].role === 'assistant') {
          const current = messages[i].content || '';
          const next = action.content || '';
          const same = current.trim() === next.trim();
          const completesStream = !current.trim() || next.startsWith(current);
          if (!same && !completesStream) {
            break;
          }
          if (!same) {
            messages[i] = { ...messages[i], content: next };
          }
          break;
        }
      }
      return { ...state, messages };
    }
    default:
      return state;
  }
}

export type { ChatResult };
