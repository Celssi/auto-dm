import type { Character } from '../../types';

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

export function hasOriginFeat(char: Character, featId: string): boolean {
  return originFeatIds(char).has(normalizeOriginFeatId(featId));
}

export function hasAlertFeat(char: Character): boolean {
  return hasOriginFeat(char, 'alert');
}

export function initiativeMod(char: Character): number {
  let mod = abilityMod(char.ability_scores?.dex ?? 10);
  if (hasAlertFeat(char)) {
    mod += proficiencyBonus(char.level || 1);
  }
  return mod;
}

export function spellAbility(classId: string): string | null {
  return SPELL_ABILITY[classId.toLowerCase()] ?? null;
}

export function spellSaveDc(char: Character): number | null {
  const ab = spellAbility(char.class_name || '');
  if (!ab) return null;
  const pb = proficiencyBonus(char.level || 1);
  return 8 + pb + abilityMod(char.ability_scores?.[ab] ?? 10);
}

export function spellAttackBonus(char: Character): number | null {
  const ab = spellAbility(char.class_name || '');
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

export function saveBonus(char: Character, ability: string): string {
  const score = char.ability_scores?.[ability] ?? 10;
  let m = abilityMod(score);
  if ((char.save_proficiencies || []).includes(ability)) {
    m += proficiencyBonus(char.level || 1);
  }
  return formatMod(m);
}
