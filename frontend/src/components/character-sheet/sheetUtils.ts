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

export function initiativeMod(char: Character): number {
  return abilityMod(char.ability_scores?.dex ?? 10);
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
