/** Placeholder for empty sheet fields (plain hyphen, not em dash). */
export const EMPTY_FIELD = '-';

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
