import type { AuditEvent } from '../../api/client';

export function formatAuditSummary(event: AuditEvent): string {
  const etype = event.event || '';
  const detail = (event.detail ?? {}) as Record<string, unknown>;
  const before = (event.before ?? {}) as Record<string, unknown>;
  const after = (event.after ?? {}) as Record<string, unknown>;

  if (etype === 'dice_roll') {
    const total = detail.total;
    const notation = detail.notation ?? '';
    return total != null ? `${notation} = ${total}` : String(notation);
  }

  if (etype === 'hp_change') {
    const b = before.hp ?? detail.hp_before;
    const a = after.hp ?? detail.hp_after;
    const dmg = detail.damage;
    if (dmg != null) return `HP ${b}→${a} (−${dmg})`;
    return `HP ${b}→${a}`;
  }

  if (etype === 'spell_slot') {
    const lvl = detail.slot_level ?? '?';
    const b = (before.spell_slots ?? {}) as Record<string, unknown>;
    const a = (after.spell_slots ?? {}) as Record<string, unknown>;
    const bs = b[String(lvl)] ?? b[lvl as string];
    const asn = a[String(lvl)] ?? a[lvl as string];
    if (bs != null && asn != null) return `L${lvl} slot ${bs}→${asn}`;
    return `Spent L${lvl} slot`;
  }

  if (etype === 'spell_cast') {
    const spell = detail.spell ?? '?';
    if (detail.ritual) return `Ritual ${spell}`;
    return `Cast ${spell}`;
  }

  if (etype === 'rest') {
    const kind = String(detail.kind ?? 'rest').replace(/_/g, ' ');
    return kind.replace(/\b\w/g, (c) => c.toUpperCase());
  }

  if (etype === 'combat_attack') {
    const hit = detail.hit;
    const dmg = detail.damage ?? 0;
    const attacker = detail.attacker ?? '?';
    return hit ? `${attacker} hit for ${dmg}` : `${attacker} miss`;
  }

  if (etype === 'combat_start') {
    const name = detail.encounter_name ?? 'Combat';
    return `Started: ${name}`;
  }

  if (etype === 'concentration') {
    const maintained = detail.maintained;
    const spell = detail.spell ?? '';
    return `Concentration ${maintained ? 'kept' : 'lost'} (${spell})`;
  }

  if (etype === 'death_save') {
    const roll = detail.roll;
    const succ = after.death_save_successes ?? detail.successes;
    const fail = after.death_save_failures ?? detail.failures;
    return `Death save ${roll} (${succ}S/${fail}F)`;
  }

  if (etype === 'character_patch') {
    const diff = (event.diff ?? {}) as Record<string, unknown>;
    const keys = Object.keys(diff);
    if (keys.length) return `Updated: ${keys.slice(0, 3).join(', ')}`;
    return 'Character updated';
  }

  if (etype === 'oracle') {
    return String(detail.summary ?? 'Oracle roll');
  }

  if (etype === 'wild_shape') {
    const uses = after.wild_shape_uses ?? detail.uses;
    const mx = detail.max;
    return `Wild Shape ${uses}/${mx}`;
  }

  return etype.replace(/_/g, ' ');
}

export function formatAuditTime(ts?: string): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return ts.slice(11, 19) || ts;
  }
}

export function isInferredAudit(event: AuditEvent): boolean {
  return event.detail?.inferred === true;
}
