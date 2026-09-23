const STAT_MAX = 20;
const STAT_MIN = 0;

export interface LegacyDeltas {
  health_delta?: number;
  morale_delta?: number;
  supplies_delta?: number;
}

function clampStat(value: number): number {
  return Math.max(STAT_MIN, Math.min(STAT_MAX, value));
}

function legacyDeltasFromOption(legacy: LegacyDeltas | undefined): [number, number, number] {
  return [Number(legacy?.health_delta ?? 0), Number(legacy?.morale_delta ?? 0), Number(legacy?.supplies_delta ?? 0)];
}

export function applyLegacyStatSwap(
  stats: { health: number; morale: number; supplies: number },
  oldLegacy: LegacyDeltas | undefined,
  newLegacy: LegacyDeltas | undefined,
): { health: number; morale: number; supplies: number } {
  const [oh, om, os] = legacyDeltasFromOption(oldLegacy);
  const [nh, nm, ns] = legacyDeltasFromOption(newLegacy);
  return {
    health: clampStat(stats.health - oh + nh),
    morale: clampStat(stats.morale - om + nm),
    supplies: clampStat(stats.supplies - os + ns),
  };
}

export function applyLegacyToBases(
  bases: { health: number; morale: number; supplies: number },
  legacy: LegacyDeltas | undefined,
): { health: number; morale: number; supplies: number } {
  const [dh, dm, ds] = legacyDeltasFromOption(legacy);
  return {
    health: clampStat(bases.health + dh),
    morale: clampStat(bases.morale + dm),
    supplies: clampStat(bases.supplies + ds),
  };
}

export function hasResourceBases(entity: Record<string, unknown>): boolean {
  const cards = entity.resource_cards as Record<string, string[]> | undefined;
  return Boolean(cards?.health?.length || cards?.morale?.length || cards?.supplies?.length);
}
