import type { LevelUpPreview } from '../types';

const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    try {
      const parsed = JSON.parse(err) as { detail?: string | { msg?: string }[] };
      if (typeof parsed.detail === 'string') {
        throw new Error(parsed.detail);
      }
      if (Array.isArray(parsed.detail)) {
        throw new Error(parsed.detail.map((d) => d.msg || JSON.stringify(d)).join('; '));
      }
    } catch (e) {
      if (e instanceof Error && e.message !== err) throw e;
    }
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const api = {
  health: () => request<{ indexed: boolean; claude_configured: boolean }>('/health'),

  getSettings: () => request<{ settings: { include_faerun: boolean; use_rerank: boolean } }>('/settings'),
  updateSettings: (settings: Partial<{ include_faerun: boolean; use_rerank: boolean }>) =>
    request<{ settings: { include_faerun: boolean; use_rerank: boolean } }>('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),

  getGames: () => request<{ games: { id: string; label: string }[] }>('/games'),

  listCharacters: () => request<{ characters: { id: string; name: string }[] }>('/characters'),
  getCharacter: (id: string) => request<{ character: Record<string, unknown> }>(`/characters/${id}`),
  getCharacterOptions: (includeFaerun = false, gameId = 'dnd5e') =>
    request<Record<string, unknown>>(
      `/characters/options?include_faerun=${includeFaerun}&game_id=${encodeURIComponent(gameId)}`,
    ),
  getCharacterSummary: (id: string) =>
    request<{ summary: Record<string, unknown>; character: Record<string, unknown> }>(`/characters/${id}/summary`),
  createCharacter: (character: Record<string, unknown>) =>
    request<{ id: string; character: Record<string, unknown> }>('/characters', {
      method: 'POST',
      body: JSON.stringify({ character }),
    }),
  previewCharacter: (character: Record<string, unknown>, finalize = true) =>
    request<{ character: Record<string, unknown> }>(`/characters/preview?finalize=${finalize ? 'true' : 'false'}`, {
      method: 'POST',
      body: JSON.stringify({ character }),
    }),
  updateCharacter: (id: string, character: Record<string, unknown>) =>
    request<{ character: Record<string, unknown> }>(`/characters/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ character }),
    }),
  getLevelUpPreview: (id: string, className?: string) =>
    request<{ preview: LevelUpPreview }>(
      `/characters/${id}/level-up-preview${className ? `?class_name=${encodeURIComponent(className)}` : ''}`,
    ),
  levelUpCharacter: (
    id: string,
    body?: {
      hp_roll?: number;
      asi_choices?: Record<string, unknown>[];
      class_name?: string;
      cantrips?: string[];
      prepared_spells?: string[];
      known_spells?: string[];
      feature_choices?: Record<string, unknown>;
      fighting_style_feat?: string;
      weapon_mastery?: string[];
      human_skill?: string;
      versatile_origin_feat?: string;
    },
  ) =>
    request<{ character: Record<string, unknown>; summary: Record<string, unknown> }>(`/characters/${id}/level-up`, {
      method: 'POST',
      body: JSON.stringify(body || {}),
    }),
  addMulticlass: (id: string, class_name: string) =>
    request<{ character: Record<string, unknown>; summary: Record<string, unknown> }>(`/characters/${id}/multiclass`, {
      method: 'POST',
      body: JSON.stringify({ class_name }),
    }),
  deleteCharacter: (id: string) => request<{ ok: boolean }>(`/characters/${id}`, { method: 'DELETE' }),

  listAdventures: (campaignId?: string) =>
    request<{ adventures: AdventureMeta[] }>(
      campaignId ? `/adventures?campaign_id=${encodeURIComponent(campaignId)}` : '/adventures',
    ),
  getAdventure: (id: string) => request<{ adventure: AdventureFull }>(`/adventures/${id}`),
  createAdventure: (body: CreateAdventureBody) =>
    request<{ id: string; adventure: AdventureFull }>('/adventures', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateAdventure: (id: string, meta: Record<string, unknown>, outline?: string) =>
    request<{ adventure: AdventureFull }>(`/adventures/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ meta, outline }),
    }),
  deleteAdventure: (id: string) => request<{ ok: boolean }>(`/adventures/${id}`, { method: 'DELETE' }),
  startAdventureSession: (adventureId: string) =>
    request<{ session_id: string; created: boolean; activated?: boolean }>(`/adventures/${adventureId}/start-session`, {
      method: 'POST',
    }),
  completeAdventure: (adventureId: string) =>
    request<{
      adventure: AdventureFull;
      next_adventure: NextAdventure | null;
      player_progress: PlayerProgress;
    }>(`/adventures/${adventureId}/complete`, { method: 'POST' }),

  listSessions: () => request<{ sessions: SessionMeta[] }>('/sessions'),
  getSession: (id: string) => request<{ session: SessionFull }>(`/sessions/${id}`),
  createSession: (body: CreateSessionBody) =>
    request<{ id: string; session: SessionFull }>('/sessions', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  deleteSession: (id: string) => request<{ ok: boolean }>(`/sessions/${id}`, { method: 'DELETE' }),

  chat: (sessionId: string, message: string) =>
    request<ChatResult>(`/sessions/${sessionId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  getShortcuts: (gameId = 'dnd5e') =>
    request<{ shortcuts: Shortcut[] }>(`/sessions/shortcuts?game_id=${encodeURIComponent(gameId)}`),
  getOracles: () => request<{ oracles: Oracle[] }>('/sessions/oracles'),
  runOracle: (sessionId: string, oracle_id: string, likelihood_level = 'fifty_fifty') =>
    request<{ summary: string }>(`/sessions/${sessionId}/oracle`, {
      method: 'POST',
      body: JSON.stringify({ oracle_id, likelihood_level }),
    }),
  runShortcut: (sessionId: string, shortcut_id: string, params?: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/sessions/${sessionId}/shortcut`, {
      method: 'POST',
      body: JSON.stringify({ shortcut_id, params: params || {} }),
    }),
  rollShortcut: (sessionId: string, shortcutId: string, params: Record<string, unknown>, preRolled?: number[]) =>
    request<ChatResult & { shortcut?: { dice?: { rolls?: number[]; total?: number }; user_message?: string } }>(
      `/sessions/${sessionId}/shortcut`,
      {
        method: 'POST',
        body: JSON.stringify({
          shortcut_id: shortcutId,
          params,
          pre_rolled: preRolled ?? null,
          narrate: true,
        }),
      },
    ),
  getLonelog: (sessionId: string) => request<{ lines: string[] }>(`/sessions/${sessionId}/lonelog`),
  getAudit: (sessionId: string, limit = 200) =>
    request<{ events: AuditEvent[] }>(`/sessions/${sessionId}/audit?limit=${limit}`),
  beginSession: (sessionId: string) => request<BeginSessionResult>(`/sessions/${sessionId}/begin`, { method: 'POST' }),
  searchRules: (question: string, include_faerun = false) =>
    request<{ answer: string; sources: Source[] }>('/rules/search', {
      method: 'POST',
      body: JSON.stringify({ question, include_faerun }),
    }),
  reindex: (include_faerun = false) =>
    request<{ ok: boolean; chunk_count: number }>('/index/reindex', {
      method: 'POST',
      body: JSON.stringify({ include_faerun }),
    }),
  getGlossary: () => request<{ count: number; entries: Record<string, unknown> }>('/glossary'),
  lookupGlossary: (names: string[], use_rag = true) =>
    request<{
      entries: Record<string, { kind: string; title: string; summary: string | null; level?: number }>;
    }>('/glossary/lookup', { method: 'POST', body: JSON.stringify({ names, use_rag }) }),

  listCampaigns: () => request<{ campaigns: CampaignMeta[] }>('/campaigns'),
  getCampaign: (id: string) => request<{ campaign: CampaignFull }>(`/campaigns/${id}`),
  listCampaignAdventures: (campaignId: string) =>
    request<{ adventures: AdventureMeta[] }>(`/campaigns/${campaignId}/adventures`),
  getCampaignEntities: (campaignId: string) =>
    request<{ entities: JournalEntity[] }>(`/campaigns/${campaignId}/entities`),
  createCampaign: (body: { name: string; story_arc?: string; character_ids?: string[] }) =>
    request<{ id: string; campaign: CampaignFull }>('/campaigns', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateCampaign: (
    id: string,
    body: { name?: string; story_arc?: string; status?: string; character_ids?: string[] },
  ) =>
    request<{ campaign: CampaignFull }>(`/campaigns/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  copyCampaign: (id: string, body: { character_id: string; name?: string }) =>
    request<{ campaign_id: string; campaign: CampaignFull }>(`/campaigns/${id}/copy`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  deleteCampaign: (id: string) => request<{ ok: boolean }>(`/campaigns/${id}`, { method: 'DELETE' }),
  getCampaignNpc: (campaignId: string, npcId: string) =>
    request<{ npc: JournalEntry }>(`/campaigns/${campaignId}/npcs/${npcId}`),
  updateCampaignNpc: (campaignId: string, npcId: string, body: { name: string; body: string }) =>
    request<{ npc: JournalEntry }>(`/campaigns/${campaignId}/npcs/${npcId}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  getCampaignLocation: (campaignId: string, locationId: string) =>
    request<{ location: JournalEntry }>(`/campaigns/${campaignId}/locations/${locationId}`),
  updateCampaignLocation: (campaignId: string, locationId: string, body: { name: string; body: string }) =>
    request<{ location: JournalEntry }>(`/campaigns/${campaignId}/locations/${locationId}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  bootstrapCampaign: (body: BootstrapCampaignBody) =>
    request<BootstrapCampaignResult>('/play/bootstrap', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  bootstrapCampaignAdventure: (body: BootstrapAdventureBody) =>
    request<BootstrapCampaignResult>('/play/bootstrap-adventure', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  generateCampaign: (body: GenerateCampaignBody) =>
    request<GenerateCampaignResult>('/play/generate-campaign', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};

export interface AdventureMeta {
  id: string;
  name: string;
  mode: string;
  status?: string;
  campaign_id?: string;
  character_id?: string;
  sequence?: number;
  source_module?: ModuleSource;
}

export interface AdventureFull extends AdventureMeta {
  theme?: string;
  log?: string;
  include_faerun?: boolean;
  campaign_id?: string;
  player_progress?: PlayerProgress;
}

export interface PlayerProgress {
  stage: string;
  completed_beats: string[];
  has_active_beat: boolean;
  adventure_complete?: boolean;
}

export interface NextAdventure {
  id: string;
  name: string;
}

export interface CombatantSnapshot {
  id: string;
  name: string;
  kind: 'player' | 'enemy' | 'ally';
  monster_name?: string;
  initiative: number;
  hp: number;
  max_hp: number;
  ac: number;
  attack_bonus?: number;
  damage?: string;
  conditions?: string[];
}

export interface CombatStateSnapshot {
  encounter_id: string;
  encounter_name: string;
  round: number;
  turn_index: number;
  current_combatant_id: string;
  order: string[];
  combatants: CombatantSnapshot[];
  status: 'active' | 'ended';
}

export interface CampaignMeta {
  id: string;
  name: string;
  status?: string;
  character_ids?: string[];
}

export interface JournalEntry {
  id: string;
  campaign_id: string;
  name: string;
  body: string;
}

export interface JournalEntity {
  kind: 'npc' | 'location';
  name: string;
  body: string;
}

export interface CampaignFull extends CampaignMeta {
  story_arc?: string;
  character_ids?: string[];
  npcs?: { id: string; name: string }[];
  locations?: { id: string; name: string }[];
  generation_mode?: string;
  source_module?: ModuleSource;
  theme?: string;
  adventure_count?: number;
}

export interface ModuleSource {
  title: string;
  source_label?: string;
  chapter?: string;
  pages?: string;
  notes?: string;
}

export interface SessionMeta {
  id: string;
  name: string;
  character_id: string;
  adventure_id: string;
}

export interface ChatMessage {
  role: string;
  content: string;
}

export interface SessionFull extends SessionMeta {
  include_faerun?: boolean;
  messages?: ChatMessage[];
  lonelog?: string;
}

export interface BeginSessionResult {
  session_id: string;
  adventure_id: string;
  opening_scene: string;
  message: ChatMessage;
}

export interface CreateAdventureBody {
  name: string;
  mode?: string;
  theme?: string;
  character_id?: string;
  campaign_id?: string;
  include_faerun?: boolean;
  outline?: string;
}

export interface CreateSessionBody {
  character_id: string;
  adventure_id: string;
  name?: string;
  include_faerun?: boolean;
}

export interface SpellConfirmation {
  requested: string;
  suggested: string;
  spell_name: string;
}

export interface ChatResult {
  response: string;
  sources: Source[];
  character: Record<string, unknown>;
  spell_confirmation?: SpellConfirmation;
  lonelog_lines?: string[];
  adventure_complete?: boolean;
  next_adventure?: NextAdventure | null;
  player_progress?: PlayerProgress;
  combat_state?: CombatStateSnapshot;
}

export interface Shortcut {
  id: string;
  label: string;
  kind: string;
}

export interface Oracle {
  id: string;
  label: string;
  kind: string;
}

export interface Source {
  source_label?: string;
  page?: string;
  text?: string;
}

export interface BootstrapCampaignBody {
  character_id: string;
  mode?: 'freeform' | 'module';
  theme: string;
  include_faerun?: boolean;
  campaign_name?: string;
}

export interface BootstrapCampaignResult {
  session_id: string;
  campaign_id: string;
  adventure_id: string;
  opening_scene: string;
  counts: { npcs: number; locations: number };
}

export interface BootstrapAdventureBody {
  campaign_id: string;
  character_id: string;
  mode?: 'freeform' | 'module';
  theme?: string;
  include_faerun?: boolean;
  adventure_name?: string;
  auto_continue?: boolean;
}

export interface GenerateCampaignBody {
  character_id?: string;
  mode?: 'freeform' | 'module';
  theme: string;
  adventure_count?: number;
  include_faerun?: boolean;
  campaign_name?: string;
  bootstrap_first?: boolean;
}

export interface GenerateCampaignResult {
  campaign_id: string;
  adventure_ids: string[];
  session_id?: string;
  adventure_id?: string;
  opening_scene?: string;
  counts: { adventures: number; npcs: number; locations: number };
}

export interface AuditEvent {
  ts?: string;
  session_id?: string;
  turn_id?: string;
  event: string;
  source?: string;
  detail?: Record<string, unknown>;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  diff?: Record<string, unknown>;
}
