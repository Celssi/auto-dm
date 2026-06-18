const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const api = {
  health: () => request<{ indexed: boolean; claude_configured: boolean }>("/health"),

  getSettings: () => request<{ settings: { include_faerun: boolean; use_rerank: boolean } }>("/settings"),
  updateSettings: (settings: Partial<{ include_faerun: boolean; use_rerank: boolean }>) =>
    request<{ settings: { include_faerun: boolean; use_rerank: boolean } }>("/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),

  listCharacters: () => request<{ characters: { id: string; name: string }[] }>("/characters"),
  getCharacter: (id: string) => request<{ character: Record<string, unknown> }>(`/characters/${id}`),
  getCharacterOptions: (includeFaerun = false) =>
    request<Record<string, unknown>>(`/characters/options?include_faerun=${includeFaerun}`),
  getCharacterSummary: (id: string) =>
    request<{ summary: Record<string, unknown>; character: Record<string, unknown> }>(`/characters/${id}/summary`),
  createCharacter: (character: Record<string, unknown>) =>
    request<{ id: string; character: Record<string, unknown> }>("/characters", {
      method: "POST",
      body: JSON.stringify({ character }),
    }),
  updateCharacter: (id: string, character: Record<string, unknown>) =>
    request<{ character: Record<string, unknown> }>(`/characters/${id}`, {
      method: "PUT",
      body: JSON.stringify({ character }),
    }),
  levelUpCharacter: (
    id: string,
    body?: { hp_roll?: number; asi_choices?: Record<string, unknown>[]; class_name?: string },
  ) =>
    request<{ character: Record<string, unknown>; summary: Record<string, unknown> }>(`/characters/${id}/level-up`, {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
  addMulticlass: (id: string, class_name: string) =>
    request<{ character: Record<string, unknown>; summary: Record<string, unknown> }>(`/characters/${id}/multiclass`, {
      method: "POST",
      body: JSON.stringify({ class_name }),
    }),
  deleteCharacter: (id: string) =>
    request<{ ok: boolean }>(`/characters/${id}`, { method: "DELETE" }),

  listAdventures: () => request<{ adventures: AdventureMeta[] }>("/adventures"),
  getAdventure: (id: string) => request<{ adventure: AdventureFull }>(`/adventures/${id}`),
  createAdventure: (body: CreateAdventureBody) =>
    request<{ id: string; adventure: AdventureFull }>("/adventures", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateAdventure: (id: string, meta: Record<string, unknown>, outline?: string) =>
    request<{ adventure: AdventureFull }>(`/adventures/${id}`, {
      method: "PUT",
      body: JSON.stringify({ meta, outline }),
    }),
  deleteAdventure: (id: string) =>
    request<{ ok: boolean }>(`/adventures/${id}`, { method: "DELETE" }),

  listSessions: () => request<{ sessions: SessionMeta[] }>("/sessions"),
  getSession: (id: string) => request<{ session: SessionFull }>(`/sessions/${id}`),
  createSession: (body: CreateSessionBody) =>
    request<{ id: string; session: SessionFull }>("/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  chat: (sessionId: string, message: string) =>
    request<ChatResult>(`/sessions/${sessionId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getShortcuts: () => request<{ shortcuts: Shortcut[] }>("/sessions/shortcuts"),
  getOracles: () => request<{ oracles: Oracle[] }>("/sessions/oracles"),
  runOracle: (sessionId: string, oracle_id: string, likelihood_level = "fifty_fifty") =>
    request<{ summary: string }>(`/sessions/${sessionId}/oracle`, {
      method: "POST",
      body: JSON.stringify({ oracle_id, likelihood_level }),
    }),
  runShortcut: (sessionId: string, shortcut_id: string, params?: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/sessions/${sessionId}/shortcut`, {
      method: "POST",
      body: JSON.stringify({ shortcut_id, params: params || {} }),
    }),
  getLonelog: (sessionId: string) =>
    request<{ lines: string[] }>(`/sessions/${sessionId}/lonelog`),
  searchRules: (question: string, include_faerun = false) =>
    request<{ answer: string; sources: Source[] }>("/rules/search", {
      method: "POST",
      body: JSON.stringify({ question, include_faerun }),
    }),
  reindex: (include_faerun = false) =>
    request<{ ok: boolean; chunk_count: number }>("/index/reindex", {
      method: "POST",
      body: JSON.stringify({ include_faerun }),
    }),

  listCampaigns: () => request<{ campaigns: CampaignMeta[] }>("/campaigns"),
  getCampaign: (id: string) => request<{ campaign: CampaignFull }>(`/campaigns/${id}`),
  createCampaign: (body: { name: string; story_arc?: string; character_ids?: string[] }) =>
    request<{ id: string; campaign: CampaignFull }>("/campaigns", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getCampaignNpc: (campaignId: string, npcId: string) =>
    request<{ npc: JournalEntry }>(`/campaigns/${campaignId}/npcs/${npcId}`),
  updateCampaignNpc: (campaignId: string, npcId: string, body: { name: string; body: string }) =>
    request<{ npc: JournalEntry }>(`/campaigns/${campaignId}/npcs/${npcId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  getCampaignLocation: (campaignId: string, locationId: string) =>
    request<{ location: JournalEntry }>(`/campaigns/${campaignId}/locations/${locationId}`),
  updateCampaignLocation: (campaignId: string, locationId: string, body: { name: string; body: string }) =>
    request<{ location: JournalEntry }>(`/campaigns/${campaignId}/locations/${locationId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  bootstrapCampaign: (body: BootstrapCampaignBody) =>
    request<BootstrapCampaignResult>("/play/bootstrap", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export interface AdventureMeta {
  id: string;
  name: string;
  mode: string;
  status?: string;
  campaign_id?: string;
}

export interface AdventureFull extends AdventureMeta {
  theme?: string;
  outline?: string;
  log?: string;
  include_faerun?: boolean;
  campaign_id?: string;
}

export interface CampaignMeta {
  id: string;
  name: string;
  status?: string;
}

export interface JournalEntry {
  id: string;
  campaign_id: string;
  name: string;
  body: string;
}

export interface CampaignFull extends CampaignMeta {
  story_arc?: string;
  character_ids?: string[];
  npcs?: { id: string; name: string }[];
  locations?: { id: string; name: string }[];
}

export interface SessionMeta {
  id: string;
  name: string;
  character_id: string;
  adventure_id: string;
}

export interface SessionFull extends SessionMeta {
  include_faerun?: boolean;
  messages?: Array<{ role: string; content: string }>;
  lonelog?: string;
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
  mode?: "freeform" | "module";
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
