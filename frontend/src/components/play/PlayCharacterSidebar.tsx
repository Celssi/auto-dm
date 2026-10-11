import type { BrambletrekCharacter, Character } from '../../types';
import { displayLabel, EMPTY_FIELD } from '../../lib/displayText';
import GlossaryTip, { GlossaryTagList } from '../ui/GlossaryTip';
import { getGameCharacterConfig } from '../../games/registry';
import {
  formatMod,
  initiativeMod,
  passivePerception,
  proficiencyBonus,
  saveBonus,
  skillBonus,
  spellSaveDc,
} from '../../games/dnd5e/character-sheet/sheetUtils';
import { STAT_COLORS, brambletrekSummaryLine, statPercent } from '../../games/brambletrek/sheetUtils';

interface Props {
  character: Character;
  summary?: Record<string, unknown>;
  gameId?: string;
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-bg/60 px-2 py-1.5 text-center min-w-[3.5rem]">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className="text-sm font-semibold text-gray-100">{value}</div>
    </div>
  );
}

export default function PlayCharacterSidebar({ character: c, summary, gameId }: Props) {
  const resolvedGameId = gameId ?? String(c.game_id || 'dnd5e');
  const config = getGameCharacterConfig(resolvedGameId);

  if (config.id === 'brambletrek') {
    return <BrambletrekPlaySidebar character={c as unknown as BrambletrekCharacter} summary={summary} />;
  }

  return <DndPlaySidebar character={c} summary={summary} />;
}

function DndPlaySidebar({ character: c, summary }: { character: Character; summary?: Record<string, unknown> }) {
  return (
    <div className="space-y-2 text-sm">
      <DndIdentity character={c} />
      <DndHitPoints character={c} />
      <DndCombatPills character={c} />
      <DndSpellSlots character={c} summary={summary} />
      <DndAbilities character={c} />
      <DndKeySkills character={c} />
      <DndSpellList character={c} />
    </div>
  );
}

function dndClassLine(c: Character) {
  const classLine = c.classes?.length
    ? c.classes.map((e) => `${displayLabel(e.class_name)} ${e.level}`).join(' · ')
    : `${displayLabel(c.class_name) || EMPTY_FIELD} ${c.level || 1}`;
  return c.subclass ? `${classLine} (${displayLabel(c.subclass)})` : classLine;
}

function DndIdentity({ character: c }: { character: Character }) {
  return (
    <div>
      <h3 className="font-semibold text-accent leading-tight">{c.name || 'Unnamed'}</h3>
      <p className="text-xs text-muted mt-0.5">
        {displayLabel(c.species) || EMPTY_FIELD} · {dndClassLine(c)}
      </p>
      {c.background && <p className="text-xs text-muted/80">{displayLabel(c.background)}</p>}
    </div>
  );
}

function DndHitPoints({ character: c }: { character: Character }) {
  const hpPct = c.max_hp ? Math.min(100, Math.round((c.hp / c.max_hp) * 100)) : 0;
  const hpColor = hpPct > 50 ? 'bg-emerald-500' : hpPct > 25 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted">Hit Points</span>
        <span className="font-medium">
          {c.hp ?? 0} / {c.max_hp ?? 0}
        </span>
      </div>
      <div className="h-2 rounded-full bg-bg overflow-hidden border border-border">
        <div className={`h-full ${hpColor} transition-[width]`} style={{ width: `${hpPct}%` }} />
      </div>
    </div>
  );
}

function DndCombatPills({ character: c }: { character: Character }) {
  const hitDiceMax = Number(c.hit_dice_max ?? c.level ?? 1);
  const hitDiceSpent = Number(c.hit_dice_spent ?? 0);
  const spellDc = spellSaveDc(c);
  return (
    <div className="flex flex-wrap gap-1.5">
      <StatPill label="AC" value={String(c.ac ?? 10)} />
      <StatPill label="Init" value={formatMod(initiativeMod(c))} />
      <StatPill label="Speed" value={`${c.speed ?? 30}`} />
      <StatPill label="PP" value={String(passivePerception(c))} />
      <StatPill label="HD" value={`${hitDiceMax - hitDiceSpent}d${c.hit_die ?? 8}`} />
      {spellDc != null && <StatPill label="Spell DC" value={String(spellDc)} />}
    </div>
  );
}

function DndSpellSlots({ character: c, summary }: { character: Character; summary?: Record<string, unknown> }) {
  const slots = c.spell_slots || {};
  const spellSlotsMax = (summary?.spell_slots_max as Record<string, number> | undefined) || {};
  const wildShapeMax = Number(summary?.wild_shape_max ?? 0);
  if (Object.keys(slots).length === 0) return null;
  return (
    <div className="rounded-md border border-border bg-bg/40 p-2">
      <div className="text-[10px] uppercase tracking-wide text-muted mb-1.5">Spell slots</div>
      <div className="flex flex-wrap gap-1">
        {Object.entries(slots).map(([lvl, n]) => (
          <SpellSlotChip key={lvl} level={lvl} remaining={n} max={spellSlotsMax[lvl]} />
        ))}
      </div>
      {c.concentration && (
        <p className="text-xs mt-2 text-accent/90">
          Concentration: <GlossaryTip name={String(c.concentration)} variant="inline" className="font-medium" />
        </p>
      )}
      {(wildShapeMax > 0 || (c.wild_shape_uses ?? 0) > 0) && (
        <p className="text-xs mt-1 text-muted">
          Wild Shape: {c.wild_shape_uses ?? 0}
          {wildShapeMax > 0 ? `/${wildShapeMax}` : ''}
        </p>
      )}
    </div>
  );
}

function SpellSlotChip({ level, remaining, max }: { level: string; remaining: number; max?: number }) {
  const label = max != null && max > 0 ? `L${level} ${remaining}/${max}` : `L${level} ${remaining}`;
  const empty = max != null && remaining === 0;
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded border ${
        empty ? 'border-red-500/40 text-red-300/80' : 'border-border text-gray-200'
      }`}
    >
      {label}
    </span>
  );
}

const KEY_SKILLS = ['perception', 'stealth', 'survival', 'athletics', 'insight', 'medicine', 'arcana', 'nature'];
const SKILL_LABELS: Record<string, string> = {
  perception: 'Perception',
  stealth: 'Stealth',
  survival: 'Survival',
  athletics: 'Athletics',
  insight: 'Insight',
  medicine: 'Medicine',
  arcana: 'Arcana',
  nature: 'Nature',
};
const SKILL_ABILITIES: Record<string, string> = {
  perception: 'wis',
  stealth: 'dex',
  survival: 'wis',
  athletics: 'str',
  insight: 'wis',
  medicine: 'wis',
  arcana: 'int',
  nature: 'int',
};

function DndAbilities({ character: c }: { character: Character }) {
  const scores = c.ability_scores || {};
  const pb = proficiencyBonus(c.level || 1);
  return (
    <div className="rounded-md border border-border bg-bg/40 p-2">
      <div className="text-[10px] uppercase tracking-wide text-muted mb-1.5">Abilities</div>
      <div className="grid grid-cols-3 gap-1 text-xs">
        {(['str', 'dex', 'con', 'int', 'wis', 'cha'] as const).map((ab) => (
          <div key={ab} className="flex justify-between gap-1 px-1 py-0.5 rounded bg-panel/50">
            <span className="uppercase text-muted">{ab}</span>
            <span>
              {scores[ab] ?? 10} <span className="text-muted">({saveBonus(c, ab)})</span>
            </span>
          </div>
        ))}
      </div>
      <p className="text-[10px] text-muted mt-1.5">Proficiency {formatMod(pb)}</p>
    </div>
  );
}

function DndKeySkills({ character: c }: { character: Character }) {
  const profs = new Set(c.skill_proficiencies || []);
  const proficientSkills = KEY_SKILLS.filter((id) => profs.has(id));
  if (proficientSkills.length === 0) return null;
  return (
    <div className="rounded-md border border-border bg-bg/40 p-2">
      <div className="text-[10px] uppercase tracking-wide text-muted mb-1">Key skills</div>
      <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-xs">
        {proficientSkills.map((id) => (
          <GlossaryTip key={id} name={id} variant="custom">
            <span className="text-gray-300 cursor-pointer">
              {SKILL_LABELS[id]} {skillBonus(c, id, SKILL_ABILITIES[id])}
            </span>
          </GlossaryTip>
        ))}
      </div>
    </div>
  );
}

function DndSpellList({ character: c }: { character: Character }) {
  const prepared = c.prepared_spells?.length ? c.prepared_spells : c.known_spells || [];
  if (!c.cantrips?.length && !c.prepared_spells?.length) return null;
  return (
    <details className="rounded-md border border-border bg-bg/40 p-2 group">
      <summary className="text-[10px] uppercase tracking-wide text-muted cursor-pointer hover:text-accent">
        Spells
      </summary>
      <div className="mt-2 space-y-2 text-xs text-gray-300">
        {c.cantrips?.length ? (
          <div>
            <span className="text-muted block mb-1">Cantrips</span>
            <GlossaryTagList items={c.cantrips} />
          </div>
        ) : null}
        {prepared.length > 0 && (
          <div>
            <span className="text-muted block mb-1">Prepared</span>
            <GlossaryTagList items={prepared} />
          </div>
        )}
      </div>
    </details>
  );
}

function StatBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = statPercent(value);
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-muted capitalize">{label}</span>
        <span className="text-xs font-semibold tabular-nums">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-bg overflow-hidden border border-border">
        <div className="h-full transition-[width]" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function BrambletrekPlaySidebar({
  character: c,
  summary,
}: {
  character: BrambletrekCharacter;
  summary?: Record<string, unknown>;
}) {
  const legacyLabel = typeof summary?.legacy === 'string' && summary.legacy ? String(summary.legacy) : c.legacy || '';

  return (
    <div className="space-y-3 text-sm">
      <div>
        <h3 className="font-semibold text-accent leading-tight">{c.name || 'Unnamed Gnawborn'}</h3>
        <p className="text-xs text-muted mt-0.5">{brambletrekSummaryLine(c, summary)}</p>
        {legacyLabel && <p className="text-xs text-muted/80">Legacy: {legacyLabel}</p>}
      </div>

      <div className="grid gap-2">
        {(['health', 'morale', 'supplies'] as const).map((k) => (
          <StatBar key={k} label={k} value={Number(c[k] ?? 10)} color={STAT_COLORS[k]} />
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5 text-xs">
        <span className="rounded-md border border-border bg-bg/60 px-2 py-1">Day {c.journey_day ?? 1}</span>
        {c.in_aldwund && (
          <span className="rounded-md border border-purple-500/30 bg-purple-500/10 px-2 py-1 text-purple-200">
            In Aldwund
          </span>
        )}
        {c.active_adventure && (
          <span className="rounded-md border border-border bg-bg/60 px-2 py-1 text-muted">{c.active_adventure}</span>
        )}
      </div>
    </div>
  );
}
