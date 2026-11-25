import type { BrambletrekCharacter } from '../../types';

const STAT_MAX = 20;

export const STAT_COLORS = {
  health: '#e05a5a',
  morale: '#6b9fff',
  supplies: '#d4a24c',
} as const;

export function statPercent(value: number): number {
  return Math.min(100, Math.max(0, (value / STAT_MAX) * 100));
}

export function brambletrekSummaryLine(char: BrambletrekCharacter, _summary?: Record<string, unknown>): string {
  // Always format from the live character. `summary.summary_line` is a snapshot
  // from session load and stays stale after Apply / Finish day.
  const day = Number(char.journey_day ?? 1);
  return `Day ${day} · HP ${Number(char.health ?? 0)} · Morale ${Number(char.morale ?? 0)} · Supplies ${Number(char.supplies ?? 0)}`;
}
