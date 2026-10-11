import type { Character } from '../../../types';
import { displayLabel, EMPTY_FIELD } from '../../../lib/displayText';
import GlossaryTip from '../../../components/ui/GlossaryTip';
import { ResourcePips, SheetField, SheetSection, SpellSlotPips, TagList } from './characterSheetViewParts';

interface Page2Props {
  character: Character;
  summary?: Record<string, unknown>;
  editable?: boolean;
  onChange?: (patch: Partial<Character>) => void;
}

const ATTUNED_SLOT_KEYS = ['attuned-slot-1', 'attuned-slot-2', 'attuned-slot-3'];

function attunedSlots(attuned: string[]) {
  const filled = (attuned.length ? attuned : [EMPTY_FIELD, EMPTY_FIELD, EMPTY_FIELD]).slice(0, 3);
  const seen = new Map<string, number>();
  return ATTUNED_SLOT_KEYS.map((slotKey, slot) => {
    const item = filled[slot] ?? EMPTY_FIELD;
    if (item === EMPTY_FIELD) return { item, key: slotKey };
    const count = (seen.get(item) ?? 0) + 1;
    seen.set(item, count);
    return { item, key: count === 1 ? item : `${item}#${count}` };
  });
}

type SpeciesTraitRow = { id: string; label: string; detail?: string; display: string; automatic?: boolean };
type OriginFeatEffectRow = { feat_id: string; feat: string; effect: string };

function page2Model(c: Character, summary?: Record<string, unknown>) {
  const attuned = (c.attuned_items as string[] | undefined) || [];
  const spellSlotsMax = (summary?.spell_slots_max as Record<string, number> | undefined) || {};
  const wildShapeMax = Number(summary?.wild_shape_max ?? 0);
  const luckPointsMax = Number(summary?.luck_points_max ?? 0);
  const luckPointsRemaining = Number(c.luck_points_remaining ?? summary?.luck_points_remaining ?? luckPointsMax);
  const showWildShape = wildShapeMax > 0 || (c.wild_shape_uses ?? 0) > 0;
  const preparedSpells = c.prepared_spells?.length ? c.prepared_spells : c.known_spells || [];
  const unlocked = summary?.unlocked_features as
    { species_traits?: SpeciesTraitRow[]; origin_feat_effects?: OriginFeatEffectRow[] } | undefined;
  return {
    attuned,
    spellSlotsMax,
    wildShapeMax,
    luckPointsMax,
    luckPointsRemaining,
    showWildShape,
    preparedSpells,
    speciesTraits: unlocked?.species_traits || [],
    originFeatEffects: unlocked?.origin_feat_effects || [],
  };
}

export default function CharacterSheetPage2({ character: c, summary, editable, onChange }: Page2Props) {
  const model = page2Model(c, summary);
  const patch = (p: Partial<Character>) => onChange?.({ ...c, ...p });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <Page2Resources
          character={c}
          spellSlotsMax={model.spellSlotsMax}
          wildShapeMax={model.wildShapeMax}
          luckPointsMax={model.luckPointsMax}
          luckPointsRemaining={model.luckPointsRemaining}
          showWildShape={model.showWildShape}
        />
        <SheetSection title="Prepared Spells" className="lg:col-span-8">
          <TagList items={model.preparedSpells} classId={c.class_name} />
        </SheetSection>
      </div>
      <Page2Gear character={c} attuned={model.attuned} />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:items-stretch">
        <Page2Languages character={c} />
        <Page2Identity
          character={c}
          editable={editable}
          speciesTraits={model.speciesTraits}
          originFeatEffects={model.originFeatEffects}
          onPatch={patch}
        />
        <Page2Notes character={c} editable={editable} onPatch={patch} />
      </div>
      <Page2Conditions character={c} />
    </div>
  );
}

function Page2Gear({ character: c, attuned }: { character: Character; attuned: string[] }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <Page2Equipment character={c} />
      <Page2Attuned attuned={attuned} />
      <Page2Currency character={c} />
    </div>
  );
}

function Page2Equipment({ character: c }: { character: Character }) {
  const inventory = c.inventory || [];
  return (
    <SheetSection title="Equipment" className="lg:col-span-6">
      {inventory.length ? (
        <ul className="space-y-1 text-sm text-gray-300">
          {inventory.map((item) => (
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
  );
}

function Page2Attuned({ attuned }: { attuned: string[] }) {
  return (
    <SheetSection title="Attuned Items" className="lg:col-span-3">
      <ul className="space-y-1 text-sm">
        {attunedSlots(attuned).map(({ item, key }) => (
          <li key={key} className={item === EMPTY_FIELD ? 'text-muted' : 'text-gray-300'}>
            {item === EMPTY_FIELD ? item : <GlossaryTip name={item} variant="inline" />}
          </li>
        ))}
      </ul>
    </SheetSection>
  );
}

function Page2Currency({ character: c }: { character: Character }) {
  return (
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
  );
}

function Page2Languages({ character: c }: { character: Character }) {
  return (
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
  );
}

function Page2Notes({
  character: c,
  editable,
  onPatch,
}: {
  character: Character;
  editable?: boolean;
  onPatch: (p: Partial<Character>) => void;
}) {
  return (
    <SheetSection title="Appearance & Notes" className="flex flex-col min-h-[16rem] md:min-h-0 md:h-full">
      <SheetField
        label=""
        hideLabel
        value={String(c.appearance || c.equipment_notes || '')}
        editable={editable}
        multiline
        fill
        plain
        onChange={(v) => onPatch({ appearance: v, equipment_notes: v })}
      />
    </SheetSection>
  );
}

function Page2Conditions({ character: c }: { character: Character }) {
  const conditions = (c.conditions as string[] | undefined) || [];
  if (conditions.length === 0) return null;
  return (
    <SheetSection title="Conditions">
      <TagList items={conditions} />
    </SheetSection>
  );
}

function Page2Resources({
  character: c,
  spellSlotsMax,
  wildShapeMax,
  luckPointsMax,
  luckPointsRemaining,
  showWildShape,
}: {
  character: Character;
  spellSlotsMax: Record<string, number>;
  wildShapeMax: number;
  luckPointsMax: number;
  luckPointsRemaining: number;
  showWildShape: boolean;
}) {
  const empty =
    Object.entries(c.spell_slots || {}).length === 0 && !showWildShape && !c.concentration && luckPointsMax <= 0;
  return (
    <SheetSection title="Resources" className="lg:col-span-4">
      {empty ? (
        <p className="text-sm text-muted">No spellcasting resources.</p>
      ) : (
        <div className="space-y-3">
          {luckPointsMax > 0 && (
            <ResourcePips label="Luck points" remaining={luckPointsRemaining} max={luckPointsMax} />
          )}
          {Object.entries(c.spell_slots || {}).map(([lvl, n]) => (
            <SpellSlotPips key={lvl} level={lvl} remaining={n} max={spellSlotsMax[lvl] ?? n} />
          ))}
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
  );
}

function Page2Identity({
  character: c,
  editable,
  speciesTraits,
  originFeatEffects,
  onPatch,
}: {
  character: Character;
  editable?: boolean;
  speciesTraits: SpeciesTraitRow[];
  originFeatEffects: OriginFeatEffectRow[];
  onPatch: (p: Partial<Character>) => void;
}) {
  return (
    <SheetSection title="Identity">
      <div className="space-y-3">
        <SheetField
          label="Alignment"
          value={c.alignment || ''}
          editable={editable}
          onChange={(v) => onPatch({ alignment: v })}
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
  );
}
