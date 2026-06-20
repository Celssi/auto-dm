/** Placeholder for empty sheet fields (plain hyphen, not em dash). */
export const EMPTY_FIELD = '-';

/** Case- and punctuation-insensitive id for spells, skills, etc. */
export function normalizeChoiceId(text: string | null | undefined): string {
  return (text ?? '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '');
}

export function resolveCanonicalChoice(stored: string, options: string[]): string | null {
  const key = normalizeChoiceId(stored);
  if (!key) return null;
  return options.find((o) => normalizeChoiceId(o) === key) ?? null;
}

export function normalizeChoiceList(values: string[], options: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const v of values) {
    const canonical = resolveCanonicalChoice(v, options) ?? v;
    const key = normalizeChoiceId(canonical);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push(canonical);
  }
  return result;
}

/** Title-case game content for display (items, spells, class ids, snake_case, etc.). */
export function displayLabel(text: string | null | undefined): string {
  if (text == null || text === '' || text === '—' || text === EMPTY_FIELD) return text ?? '';
  return text.replace(/_/g, ' ').replace(/\b[a-z]/g, (ch) => ch.toUpperCase());
}

export function displayLabels(items: string[], separator = ', '): string {
  return items
    .reduce<string[]>((acc, item) => {
      if (item) acc.push(displayLabel(item));
      return acc;
    }, [])
    .join(separator);
}
