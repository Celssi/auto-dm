import { useEffect, useState } from 'react';
import { m } from '../../lib/framer';
import { api } from '../../api/client';
import type { Character, ClassLevel } from '../../types';
import { Field } from '../ui/forms/Field';
import TextInput from '../ui/forms/TextInput';
import NumberInput from '../ui/forms/NumberInput';
import ChoiceGroup from '../ui/forms/ChoiceGroup';
import SegmentedControl from '../ui/forms/SegmentedControl';
import NumberStepper from '../ui/forms/NumberStepper';
import MultiChoice from '../ui/forms/MultiChoice';
import { displayLabel } from '../../lib/displayText';

interface Summary {
  asi_feat_slots?: number;
  asi_feat_taken?: number;
  needs_asi?: boolean;
  hit_die?: number;
  classes?: ClassLevel[];
  multiclass?: boolean;
}

interface PickBudget {
  limit_before: number;
  limit_after: number;
  current: number;
  limit_increased: boolean;
  additional_picks: number;
}

interface LevelUpPreview {
  can_level: boolean;
  reason?: string;
  target_class?: string;
  target_class_label?: string;
  class_level_before?: number;
  class_level_after?: number;
  total_level_after?: number;
  hit_die?: number;
  proficiency_bonus_increases?: boolean;
  proficiency_bonus_after?: number;
  cantrips?: PickBudget;
  class_cantrips?: PickBudget;
  spells?: PickBudget & { field: string; label: string };
  spell_list?: { cantrips: string[]; options: string[] };
  asi_this_level?: boolean;
  needs_subclass?: boolean;
  notices?: string[];
}

interface Props {
  characterId: string;
  character: Character;
  summary: Summary;
  onConfirm: (
    hpRoll: number | undefined,
    asiChoices: Record<string, unknown>[],
    className?: string,
    spells?: { cantrips?: string[]; prepared_spells?: string[]; known_spells?: string[] },
  ) => void;
  onCancel: () => void;
}

const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const;

export default function LevelUpDialog({ characterId, character, summary, onConfirm, onCancel }: Props) {
  const classEntries = (
    summary.classes?.length ? summary.classes : [{ class_name: character.class_name, level: character.level }]
  ) as ClassLevel[];
  const [targetClass, setTargetClass] = useState(classEntries[0]?.class_name || character.class_name);
  const [preview, setPreview] = useState<LevelUpPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(true);

  const selected = classEntries.find((c) => c.class_name === targetClass) || classEntries[0];
  const hitDie = preview?.hit_die || summary.hit_die || character.hit_die || 8;
  const [hpMode, setHpMode] = useState<'roll' | 'average'>('roll');
  const [hpRoll, setHpRoll] = useState<number | ''>('');
  const asiChoices = (character.asi_choices || []) as Record<string, unknown>[];
  const [localAsi, setLocalAsi] = useState<Record<string, unknown>[]>(asiChoices);
  const [localCantrips, setLocalCantrips] = useState<string[]>(character.cantrips || []);
  const spellField = (preview?.spells?.field || 'prepared_spells') as 'prepared_spells' | 'known_spells';
  const initialSpells = (character[spellField] as string[]) || [];
  const [localSpells, setLocalSpells] = useState<string[]>(initialSpells);

  const showAsi = Boolean(summary.needs_asi || preview?.asi_this_level);
  const cantripBudget = preview?.cantrips;
  const spellBudget = preview?.spells;
  const showCantripPicker = Boolean(
    preview?.spell_list?.cantrips?.length &&
      cantripBudget &&
      (cantripBudget.additional_picks > 0 || cantripBudget.limit_increased),
  );
  const showSpellPicker = Boolean(
    preview?.spell_list?.options?.length &&
      spellBudget &&
      (spellBudget.additional_picks > 0 || spellBudget.limit_increased),
  );

  useEffect(() => {
    setLocalCantrips(character.cantrips || []);
  }, [character.cantrips]);

  useEffect(() => {
    const spells = (character[spellField] as string[]) || [];
    setLocalSpells(spells);
  }, [character, spellField]);

  useEffect(() => {
    let cancelled = false;
    setLoadingPreview(true);
    api
      .getLevelUpPreview(characterId, targetClass)
      .then((res) => {
        if (!cancelled) setPreview(res.preview as unknown as LevelUpPreview);
      })
      .catch(() => {
        if (!cancelled) setPreview(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingPreview(false);
      });
    return () => {
      cancelled = true;
    };
  }, [characterId, targetClass]);

  const addAsi = () => setLocalAsi([...localAsi, { type: 'asi', plus: { str: 2 } }]);
  const addFeat = () => setLocalAsi([...localAsi, { type: 'feat', feat: '' }]);

  const confirm = () => {
    const roll = hpMode === 'average' ? Math.floor(hitDie / 2) + 1 : hpRoll === '' ? undefined : Number(hpRoll);
    const spellPayload: { cantrips?: string[]; prepared_spells?: string[]; known_spells?: string[] } = {};
    if (showCantripPicker) spellPayload.cantrips = localCantrips;
    if (showSpellPicker) spellPayload[spellField] = localSpells;
    onConfirm(roll, localAsi, targetClass, spellPayload);
  };

  const classOptions = classEntries.map((c) => ({
    value: c.class_name,
    label: `${displayLabel(c.class_name)} (Lv ${c.level})`,
  }));

  const totalAfter = preview?.total_level_after ?? character.level + 1;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <m.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="panel-glow p-6 max-w-lg w-full space-y-4 shadow-glow max-h-[90vh] overflow-y-auto"
      >
        <h2 className="font-display text-lg font-semibold text-accent">Level up → total {totalAfter}</h2>

        {preview?.target_class_label && (
          <p className="text-sm text-muted">
            {preview.target_class_label} {preview.class_level_before} → {preview.class_level_after}
          </p>
        )}

        {classEntries.length > 1 && (
          <Field label="Which class gains a level?">
            <ChoiceGroup value={targetClass} onChange={setTargetClass} options={classOptions} columns={2} />
          </Field>
        )}

        {loadingPreview && <p className="text-xs text-muted">Loading level-up changes…</p>}

        {!loadingPreview && preview?.notices && preview.notices.length > 0 && (
          <div className="rounded-lg border border-accent/25 bg-accent/5 px-3 py-2 space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-accent">At this level</p>
            <ul className="text-sm text-gray-200 space-y-1 list-disc list-inside">
              {preview.notices.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        )}

        {preview?.needs_subclass && (
          <p className="text-xs text-amber-200/90 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
            Pick a subclass in Edit after leveling if you have not already.
          </p>
        )}

        <Field label={`Hit Points (d${hitDie} + CON), ${displayLabel(selected?.class_name || character.class_name)}`}>
          <SegmentedControl
            value={hpMode}
            onChange={(v) => setHpMode(v as 'roll' | 'average')}
            options={[
              { value: 'roll', label: 'Roll' },
              { value: 'average', label: `Average (${Math.floor(hitDie / 2) + 1})` },
            ]}
          />
          {hpMode === 'roll' && (
            <NumberInput
              className="mt-2"
              min={1}
              max={hitDie}
              placeholder={`1-${hitDie}`}
              value={hpRoll}
              onChange={(e) => setHpRoll(e.target.value === '' ? '' : parseInt(e.target.value))}
            />
          )}
        </Field>

        {showCantripPicker && cantripBudget && (
          <Field
            label={`Cantrips (max ${cantripBudget.limit_after}${cantripBudget.additional_picks ? ` — pick ${cantripBudget.additional_picks} more` : ''})`}
          >
            {cantripBudget.additional_picks === 0 && cantripBudget.limit_increased && (
              <p className="text-xs text-muted mb-2">
                Limit increases to {cantripBudget.limit_after}; you already have {cantripBudget.current}. No new picks
                required.
              </p>
            )}
            <MultiChoice
              value={localCantrips}
              onChange={setLocalCantrips}
              options={preview?.spell_list?.cantrips || []}
              max={cantripBudget.limit_after}
            />
          </Field>
        )}

        {showSpellPicker && spellBudget && (
          <Field
            label={`${spellBudget.label} (max ${spellBudget.limit_after}${spellBudget.additional_picks ? ` — pick ${spellBudget.additional_picks} more` : ''})`}
          >
            {spellBudget.additional_picks === 0 && spellBudget.limit_increased && (
              <p className="text-xs text-muted mb-2">
                Limit increases to {spellBudget.limit_after}; you already have {spellBudget.current}.
              </p>
            )}
            <MultiChoice
              value={localSpells}
              onChange={setLocalSpells}
              options={preview?.spell_list?.options || []}
              max={spellBudget.limit_after}
            />
          </Field>
        )}

        {showAsi && (
          <Field label={`ASI / Feat (${summary.asi_feat_taken}/${summary.asi_feat_slots} taken)`}>
            {preview?.asi_this_level && (
              <p className="text-xs text-muted mb-2">This level grants an Ability Score Improvement or feat.</p>
            )}
            <div className="space-y-3 max-h-48 overflow-y-auto">
              {localAsi.map((choice, i) => (
                <div
                  key={`asi-${choice.type}-${i}-${choice.type === 'feat' ? String(choice.feat || '') : 'plus'}`}
                  className="text-xs border border-border rounded-lg p-3 bg-bg/30"
                >
                  {choice.type === 'feat' ? (
                    <TextInput
                      inputClassName="text-xs"
                      placeholder="Feat name"
                      value={String(choice.feat || '')}
                      onChange={(e) => {
                        const next = [...localAsi];
                        next[i] = { ...choice, feat: e.target.value };
                        setLocalAsi(next);
                      }}
                    />
                  ) : (
                    <div className="space-y-2">
                      <p className="text-muted">Assign +2 to one ability, or +1 to two:</p>
                      <div className="grid grid-cols-2 gap-2">
                        {ABILITIES.map((ab) => (
                          <NumberStepper
                            key={ab}
                            label={ab}
                            value={Number((choice.plus as Record<string, number>)?.[ab] || 0)}
                            min={0}
                            max={2}
                            onChange={(n) => {
                              const next = [...localAsi];
                              const plus = { ...(choice.plus as Record<string, number>) };
                              plus[ab] = n;
                              next[i] = { ...choice, plus };
                              setLocalAsi(next);
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-2">
              <button type="button" className="btn-ghost text-xs" onClick={addAsi}>
                + ASI
              </button>
              <button type="button" className="btn-ghost text-xs" onClick={addFeat}>
                + Feat
              </button>
            </div>
          </Field>
        )}

        <div className="flex gap-2 justify-end pt-2">
          <button type="button" className="btn-ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={confirm} disabled={loadingPreview || preview?.can_level === false}>
            Level up
          </button>
        </div>
      </m.div>
    </div>
  );
}
