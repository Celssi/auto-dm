/** Client-side PHB 2024 spell pick limits (matches character_builder.spell_limits). */

export interface ClassSpellProgression {
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
): { cantrips: number; prepared: number; known: number } {
  if (!cls?.spellcasting) {
    return { cantrips: 0, prepared: 0, known: 0 };
  }
  return {
    cantrips: byLevel(cls.cantrips_by_level, level, 0),
    prepared: byLevel(cls.prepared_by_level, level, 0),
    known: byLevel(cls.spells_known_by_level, level, 0),
  };
}

export function spellUsesKnownList(mode: string | null | undefined): boolean {
  return mode === "known" || mode === "pact";
}

export function spellPickLimit(
  mode: string | null | undefined,
  limits: { cantrips: number; prepared: number; known: number },
): number {
  return spellUsesKnownList(mode) ? limits.known : limits.prepared;
}

export function spellListField(
  mode: string | null | undefined,
): "known_spells" | "prepared_spells" {
  return spellUsesKnownList(mode) ? "known_spells" : "prepared_spells";
}

export function spellPickLabel(mode: string | null | undefined): string {
  if (mode === "pact") return "Spells known (pact magic)";
  if (mode === "known") return "Spells known";
  return "Prepared spells";
}
