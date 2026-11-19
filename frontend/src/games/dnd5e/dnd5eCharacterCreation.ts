/** Client-side PHB 2024 spell pick limits (matches character_builder.spell_limits). */

export interface ClassSpellProgression {
  id?: string;
  spellcasting?: string | null;
  cantrips_by_level?: number[];
  prepared_by_level?: number[];
  spells_known_by_level?: number[];
}

function levelIndex(level: number): number {
  return Math.max(0, Math.min(19, Number(level || 1) - 1));
}

function byLevel(table: number[] | undefined, level: number, fallback = 0): number {
  if (!Array.isArray(table) || table.length === 0) return fallback;
  return Number(table[levelIndex(level)] ?? fallback);
}

export function spellLimitsFromClass(
  cls: ClassSpellProgression | undefined,
  level: number,
): { cantrips: number; prepared: number; known: number; spellbook: number } {
  if (!cls?.spellcasting) {
    return { cantrips: 0, prepared: 0, known: 0, spellbook: 0 };
  }
  const classId = String((cls as { id?: string }).id || '').toLowerCase();
  return {
    cantrips: byLevel(cls.cantrips_by_level, level, 0),
    prepared: byLevel(cls.prepared_by_level, level, 0),
    known: byLevel(cls.spells_known_by_level, level, 0),
    spellbook: classId === 'wizard' && level > 0 ? 6 + 2 * (level - 1) : 0,
  };
}

export function highestSlotLevel(classId: string, level: number): number {
  const id = String(classId || '').toLowerCase();
  const n = Math.max(1, Number(level || 1));
  if (id === 'warlock') {
    if (n >= 9) return 5;
    if (n >= 7) return 4;
    if (n >= 5) return 3;
    if (n >= 3) return 2;
    return 1;
  }
  if (id === 'paladin' || id === 'ranger') {
    if (n >= 17) return 5;
    if (n >= 13) return 4;
    if (n >= 9) return 3;
    if (n >= 5) return 2;
    return n >= 1 ? 1 : 0;
  }
  const full = new Set(['bard', 'cleric', 'druid', 'sorcerer', 'wizard']);
  if (!full.has(id)) return 0;
  if (n >= 17) return 9;
  if (n >= 15) return 8;
  if (n >= 13) return 7;
  if (n >= 11) return 6;
  if (n >= 9) return 5;
  if (n >= 7) return 4;
  if (n >= 5) return 3;
  if (n >= 3) return 2;
  return 1;
}

function spellUsesKnownList(mode: string | null | undefined): boolean {
  return mode === 'known' || mode === 'pact';
}

export function spellListField(mode: string | null | undefined): 'known_spells' | 'prepared_spells' {
  return spellUsesKnownList(mode) ? 'known_spells' : 'prepared_spells';
}

export function spellPickLabel(mode: string | null | undefined): string {
  if (mode === 'pact') return 'Spells known (pact magic)';
  if (mode === 'known') return 'Spells known';
  return 'Prepared spells';
}
