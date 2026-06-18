import type { Character } from '../../types';
import { displayLabel, EMPTY_FIELD } from '../../lib/displayText';
import { abilityMod, formatMod, proficiencyBonus } from './sheetUtils';

export function classLine(c: Character): string {
  const entries = c.classes?.length ? c.classes : [{ class_name: c.class_name, level: c.level, subclass: c.subclass }];
  return (
    entries
      .map((e) => `${displayLabel(e.class_name)} ${e.level}${e.subclass ? ` (${displayLabel(e.subclass)})` : ''}`)
      .join(' · ') ||
    displayLabel(c.class_name) ||
    EMPTY_FIELD
  );
}

export function splitNotes(text: string): { appearance: string; backstory: string } {
  if (!text.trim()) return { appearance: '', backstory: '' };
  const appMatch = text.match(/Appearance:\s*([\s\S]*?)(?=Personality:|Status:|$)/i);
  const persMatch = text.match(/Personality:\s*([\s\S]*?)(?=Status:|$)/i);
  const appearance = appMatch?.[1]?.trim() || '';
  const backstory = persMatch?.[1]?.trim() || text.trim();
  return { appearance, backstory };
}

export function weaponAttack(c: Character, w: { ability?: string; proficient?: boolean }): string {
  const ab = w.ability || 'str';
  let m = abilityMod(c.ability_scores?.[ab] ?? 10);
  if (w.proficient) m += proficiencyBonus(c.level || 1);
  return formatMod(m);
}
