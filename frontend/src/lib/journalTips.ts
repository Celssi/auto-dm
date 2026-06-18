export interface JournalEntity {
  kind: 'npc' | 'location';
  name: string;
  body: string;
}

function escapeRegex(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function buildEntityMatcher(entities: JournalEntity[]): RegExp | null {
  const names = [...entities]
    .filter((e) => e.name.trim().length >= 2)
    .toSorted((a, b) => b.name.length - a.name.length)
    .map((e) => escapeRegex(e.name.trim()));
  if (!names.length) return null;
  return new RegExp(`(${names.join('|')})`, 'gi');
}

export function entityByMatchedName(entities: JournalEntity[], matched: string): JournalEntity | undefined {
  const lower = matched.toLowerCase();
  return entities.find((e) => e.name.toLowerCase() === lower);
}

/** Trim journal boilerplate for tooltip display. */
export function formatJournalBody(body: string): string {
  return body
    .replace(/^LAST_UPDATED:.*(\n|$)/i, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
