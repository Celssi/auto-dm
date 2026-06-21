/** Placeholder for empty sheet fields (plain hyphen, not em dash). */
export const EMPTY_FIELD = '-';

/** Case- and punctuation-insensitive id for spells, skills, etc. */
export function normalizeChoiceId(text: string | null | undefined): string {
  return (text ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '');
}

function resolveCanonicalChoice(stored: string, options: string[]): string | null {
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
  return text.replace(/_/g, ' ').replace(/(?<!')\b[a-z]/g, (ch) => ch.toUpperCase());
}

export function displayLabels(items: string[], separator = ', '): string {
  return items
    .reduce<string[]>((acc, item) => {
      if (item) acc.push(displayLabel(item));
      return acc;
    }, [])
    .join(separator);
}

/** Collect character ids from a campaign and its adventures. */
export function resolvedCampaignCharacterIds(
  characterIds: string[] | undefined,
  adventures: { character_id?: string }[] = [],
): string[] {
  const ids = [...(characterIds ?? [])];
  const seen = new Set(ids);
  for (const adv of adventures) {
    const id = adv.character_id?.trim();
    if (id && !seen.has(id)) {
      seen.add(id);
      ids.push(id);
    }
  }
  return ids;
}

function characterNamesForIds(characterIds: string[] | undefined, characters: { id: string; name: string }[]): string {
  if (!characterIds?.length) return 'No character linked';
  const names = characterIds.map((id) => characters.find((c) => c.id === id)?.name ?? displayLabel(id));
  return names.join(', ');
}

/** Resolve character label from campaign ids and/or loaded adventures. */
export function campaignCharacterLabel(
  characterIds: string[] | undefined,
  characters: { id: string; name: string }[],
  adventures: { character_id?: string }[] = [],
): string {
  return characterNamesForIds(resolvedCampaignCharacterIds(characterIds, adventures), characters);
}
