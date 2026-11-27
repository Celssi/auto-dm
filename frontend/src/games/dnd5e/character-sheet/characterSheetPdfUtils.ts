import type { Character } from '../../../types';
import { displayLabel, EMPTY_FIELD } from '../../../lib/displayText';
import { formatMod, weaponAttackBonus } from './sheetUtils';

export function featureGroupLines(groups?: Record<string, unknown>): string[] {
  return Object.entries(groups || {}).flatMap(([cid, feats]) => {
    const list = Array.isArray(feats) ? feats : [];
    return list.map((feat) => `${displayLabel(cid)}: ${displayLabel(String(feat))}`);
  });
}

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
  const backstory = persMatch?.[1]?.trim() || (appearance ? '' : text.trim());
  return { appearance, backstory };
}

export function weaponAttack(c: Character, w: { name?: string; ability?: string; proficient?: boolean }): string {
  return formatMod(weaponAttackBonus(c, w));
}
