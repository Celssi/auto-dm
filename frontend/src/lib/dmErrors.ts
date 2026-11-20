const CREDITS = 'The DM is unavailable right now (AI credits exhausted). Try again later.';
const BUSY = 'The DM is busy right now. Try again in a moment.';
const UNAVAILABLE = 'The DM is unavailable right now. Try again later.';

export function friendlyDmError(detail: unknown): string {
  const text =
    typeof detail === 'string'
      ? detail
      : detail && typeof detail === 'object' && 'detail' in detail && typeof (detail as { detail: unknown }).detail === 'string'
        ? (detail as { detail: string }).detail
        : '';
  const lower = text.toLowerCase();
  if (!lower) return UNAVAILABLE;
  if (lower.includes('credits exhausted') || lower.includes('credit balance') || lower.includes('too low')) {
    return CREDITS;
  }
  if (lower.includes('busy right now') || lower.includes('overloaded') || lower.includes('rate-limited') || lower.includes('rate limit')) {
    return BUSY;
  }
  if (lower.includes('unavailable right now')) return text;
  if (
    lower.includes('error code') ||
    lower.includes('request id') ||
    lower.includes('anthropic') ||
    lower.includes('internal server error') ||
    lower.includes('failed to generate') ||
    lower.includes('bootstrap failed')
  ) {
    return UNAVAILABLE;
  }
  return text || UNAVAILABLE;
}
