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

export function expertiseSkills(char: Character): Set<string> {
  const names = new Set<string>();
  for (const item of (char.expertise as string[] | undefined) || []) {
    if (item) names.add(String(item).toLowerCase());
  }
  const fc = (char.feature_choices || {}) as Record<string, unknown>;
  const extra = fc.rogue_expertise;
  if (Array.isArray(extra)) {
    for (const item of extra) {
      if (item) names.add(String(item).toLowerCase());
    }
  }
  return names;
}

export function skillBonusValue(char: Character, skillId: string, ability: string): number {
  const score = char.ability_scores?.[ability] ?? 10;
  let bonus = abilityMod(score);
  if ((char.skill_proficiencies || []).includes(skillId)) {
    const pb = proficiencyBonus(char.level || 1);
    bonus += expertiseSkills(char).has(skillId) ? pb * 2 : pb;
  }
  return bonus;
}

export function passivePerception(char: Character): number {
  return 10 + skillBonusValue(char, 'perception', 'wis');
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
  return formatMod(skillBonusValue(char, skillId, ability));
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

function itemBaseAndQty(label: string): { name: string; qty: number } {
  const text = String(label || '').trim();
  const match = /^(.*?)\s*\((\d+)\)\s*$/.exec(text);
  if (match) return { name: match[1].trim(), qty: Math.max(1, Number(match[2])) };
  return { name: text, qty: 1 };
}

function stackKey(name: string): string {
  let key = normItem(name);
  if (key.endsWith('ses')) return key;
  if (key.endsWith('s') && !key.endsWith('ss')) key = key.slice(0, -1);
  return key;
}

function formatCounted(name: string, qty: number): string {
  return qty <= 1 ? name : `${name} (${qty})`;
}

export function equipmentDisplayItems(char: Character): string[] {
  const items: string[] = [];
  const seen = new Set<string>();
  const armor = armorRow(String(char.armor || 'none'));
  const armorKeys = new Set(
    armor.id === 'none'
      ? []
      : [stackKey(armor.label), stackKey(armor.id), stackKey(`${armor.label} armor`), stackKey(`${armor.id} armor`)],
  );
  const add = (label: string, skip?: Set<string>) => {
    const { name, qty } = itemBaseAndQty(label);
    const key = stackKey(name);
    if (!name || key === 'none' || key === 'unarmored') return;
    if (skip && (skip.has(key) || skip.has(normItem(name)))) return;
    if (seen.has(key)) return;
    seen.add(key);
    items.push(formatCounted(name, qty));
  };
  if (armor.id !== 'none') add(armor.label);
  if (char.shield) add('Shield');
  const inventoryKeys = new Set((char.inventory || []).map((item) => stackKey(String(item))));
  for (const weapon of char.weapons || []) {
    if (inventoryKeys.has(stackKey(weapon.name))) continue;
    add(weapon.name);
  }
  for (const item of char.inventory || []) add(String(item), armorKeys);
  return items;
}

export function characterHasWeaponMastery(char: Character): boolean {
  const ids = [char.class_name, ...((char.classes as { class_name?: string }[]) || []).map((row) => row.class_name)];
  return ids.some((id) => ['barbarian', 'fighter', 'paladin', 'ranger', 'rogue'].includes(String(id || '').toLowerCase()));
}

export function weaponAttackLine(char: Character, weapon: { name: string; damage?: string; damage_type?: string; ability?: string; proficient?: boolean }): string {
  const catalogHint = String(weapon.ability || 'str').toLowerCase();
  const name = String(weapon.name || '');
  const finesse = /dagger|rapier|scimitar|shortsword|whip/i.test(name);
  const ranged = /bow|crossbow|dart|sling/i.test(name);
  let ability = catalogHint;
  if (finesse) {
    ability = abilityMod(char.ability_scores?.dex ?? 10) >= abilityMod(char.ability_scores?.str ?? 10) ? 'dex' : 'str';
  } else if (ranged) {
    ability = 'dex';
  }
  const mod = abilityMod(char.ability_scores?.[ability] ?? 10);
  const pb = proficiencyBonus(char.level || 1);
  const proficient = weapon.proficient !== false;
  const atk = mod + (proficient ? pb : 0);
  const damage = weapon.damage || '1d6';
  const dmgType = weapon.damage_type || '';
  const masteryIds = new Set((char.weapon_mastery || []).map((id) => String(id).toLowerCase().replace(/ /g, '_')));
  const weaponKey = name.toLowerCase().replace(/ /g, '_');
  const usesMastery = characterHasWeaponMastery(char) && masteryIds.has(weaponKey);
  let line = `${formatMod(atk)} to hit, ${damage}${formatMod(mod)} ${dmgType}`.trim();
  if (usesMastery) line += ', mastery';
  return line;
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
