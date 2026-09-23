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

function formatResources(char: Pick<BrambletrekCharacter, 'health' | 'morale' | 'supplies'>): string {
  return `Health ${char.health} · Morale ${char.morale} · Supplies ${char.supplies}`;
}

export function brambletrekSummaryLine(char: BrambletrekCharacter, summary?: Record<string, unknown>): string {
  const line = summary?.summary_line;
  if (typeof line === 'string' && line.trim()) return line;
  const name = char.name?.trim() || 'Unnamed Gnawborn';
  return `${name} — ${formatResources(char)}`;
}
