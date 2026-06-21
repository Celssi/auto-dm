import type { Character } from '../../types';
import { displayLabel, EMPTY_FIELD } from '../../lib/displayText';
import GlossaryTip from '../ui/GlossaryTip';
import { ResourcePips, SheetField, SheetSection, SpellSlotPips, TagList } from './characterSheetViewParts';

interface Page2Props {
  character: Character;
  summary?: Record<string, unknown>;
  editable?: boolean;
  onChange?: (patch: Partial<Character>) => void;
}

type SpeciesTraitRow = { id: string; label: string; detail?: string; display: string; automatic?: boolean };
type OriginFeatEffectRow = { feat_id: string; feat: string; effect: string };

export default function CharacterSheetPage2({ character: c, summary, editable, onChange }: Page2Props) {
  const attuned = (c.attuned_items as string[] | undefined) || [];
  const spellSlotsMax = (summary?.spell_slots_max as Record<string, number> | undefined) || {};
  const wildShapeMax = Number(summary?.wild_shape_max ?? 0);
  const luckPointsMax = Number(summary?.luck_points_max ?? 0);
  const showWildShape = wildShapeMax > 0 || (c.wild_shape_uses ?? 0) > 0;
  const preparedSpells = c.prepared_spells?.length ? c.prepared_spells : c.known_spells || [];
  const speciesTraits = ((summary?.unlocked_features as { species_traits?: SpeciesTraitRow[] } | undefined)
    ?.species_traits || []) as SpeciesTraitRow[];
  const originFeatEffects = ((summary?.unlocked_features as { origin_feat_effects?: OriginFeatEffectRow[] } | undefined)
    ?.origin_feat_effects || []) as OriginFeatEffectRow[];
  const patch = (p: Partial<Character>) => onChange?.({ ...c, ...p });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <SheetSection title="Resources" className="lg:col-span-4">
          {Object.entries(c.spell_slots || {}).length === 0 &&
          !showWildShape &&
          !c.concentration &&
          luckPointsMax <= 0 ? (
            <p className="text-sm text-muted">No spellcasting resources.</p>
          ) : (
            <div className="space-y-3">
              {luckPointsMax > 0 && <ResourcePips label="Luck points" remaining={luckPointsMax} max={luckPointsMax} />}
              {Object.entries(c.spell_slots || {}).map(([lvl, n]) => {
                const max = spellSlotsMax[lvl] ?? n;
                return <SpellSlotPips key={lvl} level={lvl} remaining={n} max={max} />;
              })}
              {showWildShape && (
                <ResourcePips
                  label="Wild Shape"
                  remaining={c.wild_shape_uses ?? 0}
                  max={wildShapeMax || (c.wild_shape_uses ?? 0)}
                />
              )}
              {c.concentration && (
                <div className="rounded-md border border-accent/30 bg-accent/5 px-3 py-2">
                  <div className="sheet-label">Concentration</div>
                  <div className="text-sm font-medium text-accent mt-0.5">
                    <GlossaryTip name={String(c.concentration)} variant="inline" />
                  </div>
                </div>
              )}
            </div>
          )}
        </SheetSection>

        <SheetSection title="Prepared Spells" className="lg:col-span-8">
          <TagList items={preparedSpells} classId={c.class_name} />
        </SheetSection>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <SheetSection title="Equipment" className="lg:col-span-6">
          {(c.inventory || []).length ? (
            <ul className="space-y-1 text-sm text-gray-300">
              {(c.inventory || []).map((item) => (
                <li key={item} className="flex gap-2 items-start">
                  <span className="text-accent/60 shrink-0">•</span>
                  <GlossaryTip name={item} variant="inline" />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">{EMPTY_FIELD}</p>
          )}
        </SheetSection>

        <SheetSection title="Attuned Items" className="lg:col-span-3">
          <ul className="space-y-1 text-sm">
            {(attuned.length ? attuned : [EMPTY_FIELD, EMPTY_FIELD, EMPTY_FIELD]).slice(0, 3).map((item, i) => (
              <li
                key={item === EMPTY_FIELD ? `attuned-slot-${i}` : item}
                className={item === EMPTY_FIELD ? 'text-muted' : 'text-gray-300'}
              >
                {item === EMPTY_FIELD ? item : <GlossaryTip name={item} variant="inline" />}
              </li>
            ))}
          </ul>
        </SheetSection>

        <SheetSection title="Currency" className="lg:col-span-3">
          <div className="grid grid-cols-5 gap-1 text-center">
            {(['cp', 'sp', 'ep', 'gp', 'pp'] as const).map((k) => (
              <div key={k} className="sheet-combat-stat !p-2">
                <div className="text-[9px] text-muted uppercase">{k}</div>
                <div className="text-sm font-semibold tabular-nums">{c.currency?.[k] || 0}</div>
              </div>
            ))}
          </div>
        </SheetSection>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:items-stretch">
        <SheetSection title="Languages & Tools">
          <div className="space-y-3">
            <div>
              <div className="sheet-label mb-1.5">Languages</div>
              <TagList items={(c.languages as string[] | undefined) || ['Common']} />
            </div>
            <div>
              <div className="sheet-label mb-1.5">Tool Proficiencies</div>
              <TagList items={(c.tool_proficiencies as string[] | undefined) || []} />
            </div>
          </div>
        </SheetSection>
        <SheetSection title="Identity">
          <div className="space-y-3">
            <SheetField
              label="Alignment"
              value={c.alignment || ''}
              editable={editable}
              onChange={(v) => patch({ alignment: v })}
            />
            <SheetField label="Size" value={displayLabel(String(c.size || 'medium'))} />
            <div className="sheet-field">
              <div className="sheet-label">Species</div>
              <div className="sheet-value">
                {c.species ? <GlossaryTip name={c.species} variant="inline" /> : EMPTY_FIELD}
              </div>
            </div>
            {speciesTraits.length > 0 && (
              <div className="sheet-field">
                <div className="sheet-label mb-1.5">Species Traits</div>
                <ul className="space-y-1.5 text-sm">
                  {speciesTraits.map((row) => (
                    <li key={row.id} className="leading-snug text-gray-300">
                      <span className="text-muted">{row.label}</span>
                      {row.detail ? (
                        <>
                          {': '}
                          {row.automatic ? (
                            <span>{row.detail}</span>
                          ) : (
                            <GlossaryTip name={row.detail} variant="inline" className="text-gray-200" />
                          )}
                        </>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {originFeatEffects.length > 0 && (
              <div className="sheet-field">
                <div className="sheet-label mb-1.5">Origin Feat Effects</div>
                <ul className="space-y-1.5 text-sm">
                  {originFeatEffects.map((row) => (
                    <li key={`${row.feat_id}-${row.effect}`} className="leading-snug text-gray-300">
                      <GlossaryTip name={row.feat} variant="inline" className="text-muted" />
                      {': '}
                      <span>{row.effect}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="sheet-field">
              <div className="sheet-label">Background</div>
              <div className="sheet-value">
                {c.background ? <GlossaryTip name={c.background} variant="inline" /> : EMPTY_FIELD}
              </div>
            </div>
          </div>
        </SheetSection>
        <SheetSection title="Appearance & Notes" className="flex flex-col min-h-[16rem] md:min-h-0 md:h-full">
          <SheetField
            label=""
            hideLabel
            value={String(c.appearance || c.equipment_notes || '')}
            editable={editable}
            multiline
            fill
            plain
            onChange={(v) => patch({ appearance: v, equipment_notes: v })}
          />
        </SheetSection>
      </div>

      {(c.conditions as string[] | undefined)?.length ? (
        <SheetSection title="Conditions">
          <TagList items={c.conditions as string[]} />
        </SheetSection>
      ) : null}
    </div>
  );
}
