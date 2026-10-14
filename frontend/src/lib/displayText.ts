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

/** Drop the technical " - play" suffix from generated session names. */
export function sessionDisplayTitle(name: string | null | undefined): string {
  const raw = (name ?? '').trim();
  if (!raw) return 'Session';
  return raw.replace(/\s+-\s+play$/i, '').trim() || raw;
}

export function formatListDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function sessionListSubtitle(characterName?: string | null, createdAt?: string | null): string {
  return [characterName?.trim(), formatListDate(createdAt)].filter(Boolean).join(' · ');
}

export type CharacterRosterEntry = {
  id: string;
  name: string;
  game_id?: string;
  species?: string;
  class_name?: string;
  level?: number;
  hp?: number;
  max_hp?: number;
  classes?: { class_name: string; level: number }[];
  legacy?: string;
  health?: number;
};

export function rosterEntryFromCharacter(
  id: string,
  name: string,
  character: Record<string, unknown>,
): CharacterRosterEntry {
  const classesRaw = character.classes;
  const classes = Array.isArray(classesRaw)
    ? classesRaw
        .filter((entry): entry is Record<string, unknown> => Boolean(entry) && typeof entry === 'object')
        .map((entry) => ({
          class_name: String(entry.class_name || ''),
          level: Number(entry.level || 1),
        }))
        .filter((entry) => entry.class_name)
    : undefined;
  return {
    id,
    name,
    game_id: typeof character.game_id === 'string' ? character.game_id : undefined,
    species: typeof character.species === 'string' ? character.species : undefined,
    class_name: typeof character.class_name === 'string' ? character.class_name : undefined,
    level: typeof character.level === 'number' ? character.level : undefined,
    hp: typeof character.hp === 'number' ? character.hp : undefined,
    max_hp: typeof character.max_hp === 'number' ? character.max_hp : undefined,
    classes,
    legacy: typeof character.legacy === 'string' ? character.legacy : undefined,
    health: typeof character.health === 'number' ? character.health : undefined,
  };
}

/** Species, class, level, and HP for character list cards. */
export function characterRosterSubtitle(entry: CharacterRosterEntry): string {
  if ((entry.game_id || '') === 'brambletrek') {
    const parts = [
      entry.legacy ? displayLabel(entry.legacy) : '',
      entry.health != null ? `Health ${entry.health}` : '',
    ];
    return parts.filter(Boolean).join(' · ');
  }
  const classLine = entry.classes?.length
    ? entry.classes.map((item) => `${displayLabel(item.class_name)} ${item.level}`).join(' · ')
    : [displayLabel(entry.class_name), entry.level != null ? String(entry.level) : ''].filter(Boolean).join(' ');
  const identity = [displayLabel(entry.species), classLine].filter(Boolean).join(' · ');
  const hp =
    entry.hp != null && entry.max_hp != null
      ? `HP ${entry.hp}/${entry.max_hp}`
      : entry.hp != null
        ? `HP ${entry.hp}`
        : '';
  return [identity, hp].filter(Boolean).join(' · ');
}

/** Resolve character label from campaign ids and/or loaded adventures. */
export function campaignCharacterLabel(
  characterIds: string[] | undefined,
  characters: { id: string; name: string }[],
  adventures: { character_id?: string }[] = [],
): string {
  return characterNamesForIds(resolvedCampaignCharacterIds(characterIds, adventures), characters);
}
