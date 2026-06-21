/** Normalize glossary lookup keys (matches backend). */
export function glossaryKey(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '');
}

/** Strip quantity suffix and simple plural for equipment lookup. */
function normalizeLookupName(name: string): string {
  const base = name.replace(/\s*\(\s*\d+\s*\)\s*$/, '').trim();
  let nk = glossaryKey(base);
  if (nk.endsWith('s') && nk.length > 3) {
    const singular = nk.slice(0, -1);
    if (singular.length >= 3) nk = singular;
  }
  return nk;
}

export interface GlossaryEntry {
  kind: string;
  title: string;
  summary: string | null;
  level?: number;
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function lookupGlossary(
  name: string,
  entries: Record<string, GlossaryEntry>,
  classId?: string,
): GlossaryEntry | null {
  const candidates: string[] = [];
  if (classId) {
    candidates.push(glossaryKey(`${classId}_${name}`));
  }
  candidates.push(glossaryKey(name));
  const paren = name.split('(')[0].trim();
  if (paren !== name) {
    candidates.push(glossaryKey(paren));
  }
  candidates.push(normalizeLookupName(name));
  for (const key of candidates) {
    const hit = entries[key];
    if (hit?.summary) return hit;
  }
  return fuzzyGlossaryLookup(name, entries);
}

function fuzzyGlossaryLookup(name: string, entries: Record<string, GlossaryEntry>): GlossaryEntry | null {
  const key = glossaryKey(name);
  const exact = entries[key];
  if (exact?.summary) return exact;
  if (key.length < 8) return exact ?? null;

  const candidates = Object.entries(entries)
    .filter(([k, entry]) => k.length >= 4 && entry.summary)
    .toSorted((a, b) => b[0].length - a[0].length);

  if (candidates.length === 0) return null;

  const pattern = candidates.map(([k]) => escapeRegex(k)).join('|');
  const re = new RegExp(pattern, 'g');
  let best: GlossaryEntry | null = null;
  let bestLen = 0;
  for (const match of key.matchAll(re)) {
    const k = match[0];
    if (k.length > bestLen) {
      const entry = entries[k];
      if (entry) {
        best = entry;
        bestLen = k.length;
      }
    }
  }
  return best;
}
