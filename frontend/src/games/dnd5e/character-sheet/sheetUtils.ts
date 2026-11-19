import type { Character } from '../../../types';

const SPELL_ABILITY: Record<string, string> = {
  bard: 'cha',
  cleric: 'wis',
  druid: 'wis',
  paladin: 'cha',
  ranger: 'wis',
  sorcerer: 'cha',
  warlock: 'cha',
  wizard: 'int',
};

export function abilityMod(score: number): number {
  return Math.floor((score - 10) / 2);
}

export function formatMod(m: number): string {
  return m >= 0 ? `+${m}` : `${m}`;
}

export function formatAbilityMod(score: number): string {
  return formatMod(abilityMod(score));
}

export function proficiencyBonus(level: number): number {
  return 2 + Math.floor((Math.max(1, level) - 1) / 4);
}

export function passivePerception(char: Character): number {
  const wis = char.ability_scores?.wis ?? 10;
  let pp = 10 + abilityMod(wis);
  if ((char.skill_proficiencies || []).includes('perception')) {
    pp += proficiencyBonus(char.level || 1);
  }
  return pp;
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
    if (labelNorm === norm || fid === key) return fid;
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

function hasOriginFeat(char: Character, featId: string): boolean {
  return originFeatIds(char).has(normalizeOriginFeatId(featId));
}

function hasAlertFeat(char: Character): boolean {
  return hasOriginFeat(char, 'alert');
}

export function initiativeMod(char: Character): number {
  let mod = abilityMod(char.ability_scores?.dex ?? 10);
  if (hasAlertFeat(char)) {
    mod += proficiencyBonus(char.level || 1);
  }
  return mod;
}

export function spellAbility(classId: string, subclass?: string): string | null {
  const sub = String(subclass || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_');
  if (sub.includes('eldritch_knight') || sub.includes('eldritch')) return 'int';
  if (sub.includes('arcane_trickster') || sub.includes('trickster')) return 'int';
  return SPELL_ABILITY[classId.toLowerCase()] ?? null;
}

export function spellSaveDc(char: Character): number | null {
  const ab = spellAbility(char.class_name || '', char.subclass);
  if (!ab) return null;
  const pb = proficiencyBonus(char.level || 1);
  return 8 + pb + abilityMod(char.ability_scores?.[ab] ?? 10);
}

export function spellAttackBonus(char: Character): number | null {
  const ab = spellAbility(char.class_name || '', char.subclass);
  if (!ab) return null;
  const pb = proficiencyBonus(char.level || 1);
  return pb + abilityMod(char.ability_scores?.[ab] ?? 10);
}

export function skillBonus(char: Character, skillId: string, ability: string): string {
  const score = char.ability_scores?.[ability] ?? 10;
  let m = abilityMod(score);
  if ((char.skill_proficiencies || []).includes(skillId)) {
    m += proficiencyBonus(char.level || 1);
  }
  return formatMod(m);
}

export const ARMOR_CATALOG = [
  { id: 'none', label: 'Unarmored', category: 'none', base: 10, dex: 'full' as const },
  { id: 'padded', label: 'Padded', category: 'light', base: 11, dex: 'full' as const },
  { id: 'leather', label: 'Leather', category: 'light', base: 11, dex: 'full' as const },
  { id: 'studded_leather', label: 'Studded Leather', category: 'light', base: 12, dex: 'full' as const },
  { id: 'hide', label: 'Hide', category: 'medium', base: 12, dex: 'cap2' as const },
  { id: 'chain_shirt', label: 'Chain Shirt', category: 'medium', base: 13, dex: 'cap2' as const },
  { id: 'scale_mail', label: 'Scale Mail', category: 'medium', base: 14, dex: 'cap2' as const },
  { id: 'breastplate', label: 'Breastplate', category: 'medium', base: 14, dex: 'cap2' as const },
  { id: 'half_plate', label: 'Half Plate', category: 'medium', base: 15, dex: 'cap2' as const },
  { id: 'ring_mail', label: 'Ring Mail', category: 'heavy', base: 14, dex: 'none' as const },
  { id: 'chain_mail', label: 'Chain Mail', category: 'heavy', base: 16, dex: 'none' as const },
  { id: 'splint', label: 'Splint', category: 'heavy', base: 17, dex: 'none' as const },
  { id: 'plate', label: 'Plate', category: 'heavy', base: 18, dex: 'none' as const },
] as const;

function normItem(name: string): string {
  return String(name || '')
    .trim()
    .toLowerCase()
    .replace(/['’]/g, '')
    .replace(/[_-]+/g, ' ');
}

export function armorRow(armorId?: string) {
  const id =
    String(armorId || 'none')
      .trim()
      .toLowerCase() || 'none';
  return ARMOR_CATALOG.find((row) => row.id === id) || ARMOR_CATALOG[0];
}

export function computeAcDetails(char: Character): {
  ac: number;
  formula: string;
  parts: { label: string; value: number }[];
} {
  const dex = abilityMod(char.ability_scores?.dex ?? 10);
  const armor = armorRow(String(char.armor || 'none'));
  const parts: { label: string; value: number }[] = [];
  let computed: number = armor.base;
  parts.push({ label: armor.label, value: armor.base });
  if (armor.dex === 'full' && dex) {
    computed += dex;
    parts.push({ label: 'Dexterity', value: dex });
  } else if (armor.dex === 'cap2') {
    const added = Math.min(dex, 2);
    if (added) {
      computed += added;
      parts.push({ label: 'Dexterity (max +2)', value: added });
    }
  }
  if (char.shield) {
    computed += 2;
    parts.push({ label: 'Shield', value: 2 });
  }
  const style = String(char.fighting_style_feat || '').toLowerCase();
  if (style === 'defense' && armor.category !== 'none') {
    computed += 1;
    parts.push({ label: 'Defense', value: 1 });
  }
  computed = Math.max(1, Math.min(30, computed));
  const formula = `${parts.map((p) => `${p.label} ${p.value}`).join(' + ')} = ${computed}`;
  return { ac: char.ac_manual ? Number(char.ac || computed) : computed, formula, parts };
}

export function equipmentDisplayItems(char: Character): string[] {
  const seen = new Set<string>();
  const items: string[] = [];
  const add = (label: string) => {
    const text = String(label || '').trim();
    const key = normItem(text);
    if (!text || key === 'none' || key === 'unarmored' || seen.has(key)) return;
    seen.add(key);
    items.push(text);
  };
  const armor = armorRow(String(char.armor || 'none'));
  if (armor.id !== 'none') add(armor.label);
  if (char.shield) add('Shield');
  for (const weapon of char.weapons || []) add(weapon.name);
  for (const item of char.inventory || []) add(item);
  return items;
}

export function weaponMasteryWarnings(char: Character): string[] {
  const owned = new Set([...(char.weapons || []).map((w) => w.name), ...(char.inventory || [])].map(normItem));
  const warnings: string[] = [];
  for (const raw of char.weapon_mastery || []) {
    const label = String(raw || '').replace(/_/g, ' ');
    const key = normItem(label);
    if (!key) continue;
    const aliases = new Set([key, normItem(String(raw))]);
    if ([...aliases].every((alias) => !owned.has(alias))) {
      warnings.push(`Weapon Mastery includes ${label}, but this character does not currently own that weapon.`);
    }
  }
  return warnings;
}

export function saveBonus(char: Character, ability: string): string {
  const score = char.ability_scores?.[ability] ?? 10;
  let m = abilityMod(score);
  if ((char.save_proficiencies || []).includes(ability)) {
    m += proficiencyBonus(char.level || 1);
  }
  return formatMod(m);
}
