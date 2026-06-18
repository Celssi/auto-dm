import type { Character } from '../../types';
import { displayLabel, EMPTY_FIELD } from '../../lib/displayText';
import GlossaryTip, { GlossaryTagList } from '../ui/GlossaryTip';
import {
  formatMod,
  initiativeMod,
  passivePerception,
  proficiencyBonus,
  saveBonus,
  skillBonus,
  spellSaveDc,
} from '../character-sheet/sheetUtils';

interface Props {
  character: Character;
  summary?: Record<string, unknown>;
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-bg/60 px-2 py-1.5 text-center min-w-[3.5rem]">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className="text-sm font-semibold text-gray-100">{value}</div>
    </div>
  );
}

export default function PlayCharacterSidebar({ character: c, summary }: Props) {
  const scores = c.ability_scores || {};
  const profs = new Set(c.skill_proficiencies || []);
  const pb = proficiencyBonus(c.level || 1);
  const spellSlotsMax = (summary?.spell_slots_max as Record<string, number> | undefined) || {};
  const wildShapeMax = Number(summary?.wild_shape_max ?? 0);
  const hitDiceMax = Number(c.hit_dice_max ?? c.level ?? 1);
  const hitDiceSpent = Number(c.hit_dice_spent ?? 0);
  const hpPct = c.max_hp ? Math.min(100, Math.round((c.hp / c.max_hp) * 100)) : 0;
  const hpColor = hpPct > 50 ? 'bg-emerald-500' : hpPct > 25 ? 'bg-amber-500' : 'bg-red-500';

  const classLine =
    (c.classes?.length
      ? c.classes.map((e) => `${displayLabel(e.class_name)} ${e.level}`).join(' · ')
      : `${displayLabel(c.class_name) || EMPTY_FIELD} ${c.level || 1}`) +
    (c.subclass ? ` (${displayLabel(c.subclass)})` : '');

  const proficientSkills = [
    'perception',
    'stealth',
    'survival',
    'athletics',
    'insight',
    'medicine',
    'arcana',
    'nature',
  ].filter((id) => profs.has(id));

  return (
    <div className="space-y-2 text-sm">
      <div>
        <h3 className="font-semibold text-accent leading-tight">{c.name || 'Unnamed'}</h3>
        <p className="text-xs text-muted mt-0.5">
          {displayLabel(c.species) || EMPTY_FIELD} · {classLine}
        </p>
        {c.background && <p className="text-xs text-muted/80">{displayLabel(c.background)}</p>}
      </div>

      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-muted">Hit Points</span>
          <span className="font-medium">
            {c.hp ?? 0} / {c.max_hp ?? 0}
          </span>
        </div>
        <div className="h-2 rounded-full bg-bg overflow-hidden border border-border">
          <div className={`h-full ${hpColor} transition-all`} style={{ width: `${hpPct}%` }} />
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <StatPill label="AC" value={String(c.ac ?? 10)} />
        <StatPill label="Init" value={formatMod(initiativeMod(c))} />
        <StatPill label="Speed" value={`${c.speed ?? 30}`} />
        <StatPill label="PP" value={String(passivePerception(c))} />
        <StatPill label="HD" value={`${hitDiceMax - hitDiceSpent}d${c.hit_die ?? 8}`} />
        {spellSaveDc(c) != null && <StatPill label="Spell DC" value={String(spellSaveDc(c))} />}
      </div>

      {Object.keys(c.spell_slots || {}).length > 0 && (
        <div className="rounded-md border border-border bg-bg/40 p-2">
          <div className="text-[10px] uppercase tracking-wide text-muted mb-1.5">Spell slots</div>
          <div className="flex flex-wrap gap-1">
            {Object.entries(c.spell_slots || {}).map(([lvl, n]) => {
              const max = spellSlotsMax[lvl];
              const label = max != null && max > 0 ? `L${lvl} ${n}/${max}` : `L${lvl} ${n}`;
              const empty = max != null ? n === 0 : false;
              return (
                <span
                  key={lvl}
                  className={`text-xs px-2 py-0.5 rounded border ${
                    empty ? 'border-red-500/40 text-red-300/80' : 'border-border text-gray-200'
                  }`}
                >
                  {label}
                </span>
              );
            })}
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
      )}

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

      {proficientSkills.length > 0 && (
        <div className="rounded-md border border-border bg-bg/40 p-2">
          <div className="text-[10px] uppercase tracking-wide text-muted mb-1">Key skills</div>
          <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-xs">
            {proficientSkills.map((id) => {
              const labels: Record<string, string> = {
                perception: 'Perception',
                stealth: 'Stealth',
                survival: 'Survival',
                athletics: 'Athletics',
                insight: 'Insight',
                medicine: 'Medicine',
                arcana: 'Arcana',
                nature: 'Nature',
              };
              const abMap: Record<string, string> = {
                perception: 'wis',
                stealth: 'dex',
                survival: 'wis',
                athletics: 'str',
                insight: 'wis',
                medicine: 'wis',
                arcana: 'int',
                nature: 'int',
              };
              return (
                <GlossaryTip key={id} name={id} variant="custom">
                  <span className="text-gray-300 cursor-help">
                    {labels[id]} {skillBonus(c, id, abMap[id])}
                  </span>
                </GlossaryTip>
              );
            })}
          </div>
        </div>
      )}

      {c.cantrips?.length || c.prepared_spells?.length ? (
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
            {c.prepared_spells?.length || c.known_spells?.length ? (
              <div>
                <span className="text-muted block mb-1">Prepared</span>
                <GlossaryTagList items={c.prepared_spells?.length ? c.prepared_spells : c.known_spells || []} />
              </div>
            ) : null}
          </div>
        </details>
      ) : null}
    </div>
  );
}
