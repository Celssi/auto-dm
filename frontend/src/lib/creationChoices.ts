import type { Character } from '../types';

export interface CreationChoiceOption {
  id: string;
  label: string;
  [key: string]: unknown;
}

export interface CreationChoiceDef {
  id: string;
  kind: string;
  label: string;
  help?: string;
  count?: number;
  min_level?: number;
  options?: CreationChoiceOption[] | string;
  spell_options?: string[];
  spell_list?: string;
  spell_level?: number;
}

export interface CreationChoiceCatalog {
  species?: Record<string, CreationChoiceDef[]>;
  classes?: Record<string, CreationChoiceDef[]>;
  origin_feat_subchoices?: Record<string, { when_feat?: string[]; choices?: CreationChoiceDef[] }>;
  fighting_style_feats?: CreationChoiceOption[];
  origin_feats?: CreationChoiceOption[];
  draconic_ancestries?: CreationChoiceOption[];
  elven_lineages?: CreationChoiceOption[];
  gnome_lineages?: CreationChoiceOption[];
  giant_ancestries?: CreationChoiceOption[];
  fiendish_legacies?: CreationChoiceOption[];
  favored_enemies?: CreationChoiceOption[];
  divine_orders?: CreationChoiceOption[];
  primal_orders?: CreationChoiceOption[];
  eldritch_invocations?: CreationChoiceOption[];
}

const ORIGIN_FEAT_LABELS: Record<string, string> = {
  alert: 'Alert',
  crafter: 'Crafter',
  healer: 'Healer',
  lucky: 'Lucky',
  magic_initiate_cleric: 'Magic Initiate (Cleric)',
  magic_initiate_druid: 'Magic Initiate (Druid)',
  magic_initiate_wizard: 'Magic Initiate (Wizard)',
  musician: 'Musician',
  savage_attacker: 'Savage Attacker',
  skilled: 'Skilled',
  tavern_brawler: 'Tavern Brawler',
  tough: 'Tough',
};

function normalizeOriginFeatId(raw: string): string {
  const text = String(raw || '').trim();
  if (!text) return '';
  const key = text.toLowerCase().replace(/ /g, '_');
  if (key in ORIGIN_FEAT_LABELS) return key;
  const norm = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '');
  for (const [fid, label] of Object.entries(ORIGIN_FEAT_LABELS)) {
    const labelNorm = label.toLowerCase().replace(/[^a-z0-9]+/g, '_');
    if (labelNorm === norm) return fid;
  }
  return key;
}

function originFeatIds(char: Character): Set<string> {
  const ids = new Set<string>();
  for (const raw of [char.origin_feat, char.versatile_origin_feat]) {
    const fid = normalizeOriginFeatId(String(raw || ''));
    if (fid) ids.add(fid);
  }
  return ids;
}

function featMatchesWhenList(when: string[], char: Character): boolean {
  const active = originFeatIds(char);
  return when.some((entry) => active.has(normalizeOriginFeatId(entry)));
}

function expandChoice(
  raw: CreationChoiceDef,
  options: Record<string, unknown>,
  catalog: CreationChoiceCatalog,
): CreationChoiceDef {
  const opts = raw.options;
  if (typeof opts === 'string' && opts.startsWith('$')) {
    const key = opts.slice(1);
    if (key === 'skills') {
      return {
        ...raw,
        options: ((options.skills as { id: string; label: string }[]) || []).map((s) => ({
          id: s.id,
          label: s.label,
        })),
      };
    }
    if (key === 'weapons') {
      return {
        ...raw,
        options: ((options.weapons as { id: string; label: string }[]) || []).map((w) => ({
          id: w.id,
          label: w.label,
        })),
      };
    }
    if (key === 'languages') {
      return {
        ...raw,
        options: ((options.languages as string[]) || []).map((l) => ({
          id: l.replace(/ /g, '_'),
          label: l.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        })),
      };
    }
    const ref = catalog[key as keyof CreationChoiceCatalog];
    if (Array.isArray(ref)) return { ...raw, options: ref as CreationChoiceOption[] };
  }
  return raw;
}

export function choicesForDraft(
  char: Character,
  options: Record<string, unknown>,
  catalog: CreationChoiceCatalog,
): CreationChoiceDef[] {
  const out: CreationChoiceDef[] = [];
  const speciesId = String(char.species || '').toLowerCase();
  const classId = String(char.class_name || '').toLowerCase();
  const level = Number(char.level || 1);

  for (const raw of catalog.species?.[speciesId] || []) {
    out.push(expandChoice(raw, options, catalog));
  }

  for (const raw of catalog.classes?.[classId] || []) {
    const minLv = Number(raw.min_level || 1);
    if (level >= minLv) out.push(expandChoice(raw, options, catalog));
  }

  for (const block of Object.values(catalog.origin_feat_subchoices || {})) {
    const when = block.when_feat || [];
    if (!featMatchesWhenList(when, char)) continue;
    for (const raw of block.choices || []) {
      const expanded = expandChoice(raw, options, catalog);
      if (expanded.spell_options?.length) {
        out.push(expanded);
      } else if (raw.spell_list) {
        const spellLists = (options.spell_lists || {}) as Record<string, Record<string, string[]>>;
        const sl = spellLists[String(raw.spell_list)] || {};
        const spellLevel = Number(raw.spell_level ?? 0);
        const key = spellLevel === 0 ? 'cantrips' : String(spellLevel);
        out.push({ ...expanded, spell_options: sl[key] || sl.cantrips || [] });
      } else {
        out.push(expanded);
      }
    }
  }
  return out;
}

export function getChoiceValue(char: Character, choiceId: string): unknown {
  const fc = (char.feature_choices || {}) as Record<string, unknown>;
  if (choiceId === 'human_skill') return char.human_skill || fc.human_skill;
  if (choiceId === 'fighting_style_feat') return char.fighting_style_feat || fc.fighting_style_feat;
  if (choiceId === 'versatile_origin_feat') return char.versatile_origin_feat || fc.versatile_origin_feat;
  if (choiceId === 'weapon_mastery') return char.weapon_mastery || fc.weapon_mastery;
  if (choiceId === 'size') return char.size;
  return fc[choiceId];
}

export function patchChoice(char: Character, choiceId: string, value: unknown): Partial<Character> {
  const fc = { ...((char.feature_choices || {}) as Record<string, unknown>), [choiceId]: value };
  const patch: Partial<Character> = { feature_choices: fc };
  if (choiceId === 'human_skill') patch.human_skill = String(value || '');
  if (choiceId === 'fighting_style_feat') patch.fighting_style_feat = String(value || '');
  if (choiceId === 'versatile_origin_feat') patch.versatile_origin_feat = String(value || '');
  if (choiceId === 'weapon_mastery') patch.weapon_mastery = value as string[];
  if (choiceId === 'size') patch.size = String(value || 'medium');
  return patch;
}

export function validateChoices(char: Character, choices: CreationChoiceDef[]): string[] {
  const missing: string[] = [];
  for (const choice of choices) {
    const val = getChoiceValue(char, choice.id);
    const count = Number(choice.count || 1);
    const kind = choice.kind;
    if (kind === 'weapons' || kind === 'skills' || kind === 'invocations' || kind === 'spells') {
      const items = Array.isArray(val) ? val : [];
      if (items.length < count) missing.push(`${choice.label}: pick ${count}`);
    } else if (!val) {
      missing.push(`${choice.label}: required`);
    }
  }
  return missing;
}
