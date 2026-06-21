import { useEffect, useReducer, useState } from 'react';
import { m } from '../../../lib/framer';
import { api } from '../../../api/client';
import type { Character, ClassLevel, LevelUpPreview } from '../../../types';
import CreationChoicesForm from './CreationChoicesForm';
import type { CreationChoiceDef } from '../../../lib/creationChoices';
import { Field } from '../../../components/ui/forms/Field';
import TextInput from '../../../components/ui/forms/TextInput';
import NumberInput from '../../../components/ui/forms/NumberInput';
import ChoiceGroup from '../../../components/ui/forms/ChoiceGroup';
import SegmentedControl from '../../../components/ui/forms/SegmentedControl';
import NumberStepper from '../../../components/ui/forms/NumberStepper';
import MultiChoice from '../../../components/ui/forms/MultiChoice';
import { displayLabel } from '../../../lib/displayText';

interface Summary {
  asi_feat_slots?: number;
  asi_feat_taken?: number;
  needs_asi?: boolean;
  hit_die?: number;
  classes?: ClassLevel[];
  multiclass?: boolean;
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
    choices?: Partial<Character>,
  ) => void;
  onCancel: () => void;
}

const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const;

type PreviewState = {
  key: string;
  preview: LevelUpPreview | null;
  loading: boolean;
};

type PreviewAction = { type: 'start'; key: string } | { type: 'finish'; key: string; preview: LevelUpPreview | null };

function previewReducer(_state: PreviewState, action: PreviewAction): PreviewState {
  switch (action.type) {
    case 'start':
      return { key: action.key, preview: null, loading: true };
    case 'finish':
      return { key: action.key, preview: action.preview, loading: false };
    default:
      return _state;
  }
}

type FormState = {
  key: string;
  targetClass: string;
  hpMode: 'roll' | 'average';
  hpRoll: number | '';
  localAsi: Record<string, unknown>[];
  localCantrips: string[];
  localSpells: string[];
};

type FormAction =
  | { type: 'reset'; key: string; character: Character; spellField: 'prepared_spells' | 'known_spells' }
  | { type: 'setTargetClass'; className: string; character: Character; spellField: 'prepared_spells' | 'known_spells' }
  | { type: 'setHpMode'; mode: 'roll' | 'average' }
  | { type: 'setHpRoll'; value: number | '' }
  | { type: 'setLocalAsi'; value: Record<string, unknown>[] }
  | { type: 'setLocalCantrips'; value: string[] }
  | { type: 'setLocalSpells'; value: string[] };

function createFormState(
  key: string,
  character: Character,
  targetClass: string,
  spellField: 'prepared_spells' | 'known_spells',
): FormState {
  return {
    key,
    targetClass,
    hpMode: 'roll',
    hpRoll: '',
    localAsi: (character.asi_choices || []) as Record<string, unknown>[],
    localCantrips: character.cantrips || [],
    localSpells: spellValuesForField(character, spellField),
  };
}

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case 'reset':
      return createFormState(action.key, action.character, state.targetClass, action.spellField);
    case 'setTargetClass':
      return {
        ...createFormState(state.key, action.character, action.className, action.spellField),
        targetClass: action.className,
      };
    case 'setHpMode':
      return { ...state, hpMode: action.mode };
    case 'setHpRoll':
      return { ...state, hpRoll: action.value };
    case 'setLocalAsi':
      return { ...state, localAsi: action.value };
    case 'setLocalCantrips':
      return { ...state, localCantrips: action.value };
    case 'setLocalSpells':
      return { ...state, localSpells: action.value };
    default:
      return state;
  }
}

function spellValuesForField(character: Character, field: 'prepared_spells' | 'known_spells') {
  return (character[field] as string[]) || [];
}

export default function LevelUpDialog({ characterId, character, summary, onConfirm, onCancel }: Props) {
  const classEntries = (
    summary.classes?.length ? summary.classes : [{ class_name: character.class_name, level: character.level }]
  ) as ClassLevel[];
  const initialTargetClass = classEntries[0]?.class_name || character.class_name;
  const initialSpellField = 'prepared_spells' as const;
  const [form, dispatchForm] = useReducer(formReducer, undefined, () =>
    createFormState(`${characterId}:${initialTargetClass}`, character, initialTargetClass, initialSpellField),
  );
  const [previewState, dispatchPreview] = useReducer(previewReducer, {
    key: '',
    preview: null,
    loading: true,
  });
  const [options, setOptions] = useState<Record<string, unknown>>({});
  const [choicePatch, setChoicePatch] = useState<Partial<Character>>({});

  const { targetClass, hpMode, hpRoll, localAsi, localCantrips, localSpells } = form;

  const selected = classEntries.find((c) => c.class_name === targetClass) || classEntries[0];
  const preview = previewState.preview;
  const loadingPreview = previewState.loading;
  const hitDie = preview?.hit_die || summary.hit_die || character.hit_die || 8;
  const spellField = (preview?.spells?.field || 'prepared_spells') as 'prepared_spells' | 'known_spells';
  const formKey = `${characterId}:${targetClass}:${spellField}`;

  if (formKey !== form.key) {
    dispatchForm({ type: 'reset', key: formKey, character, spellField });
  }

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
    api
      .getCharacterOptions(false)
      .then(setOptions)
      .catch(() => setOptions({}));
  }, []);

  useEffect(() => {
    const key = `${characterId}:${targetClass}`;
    let cancelled = false;
    dispatchPreview({ type: 'start', key });
    api
      .getLevelUpPreview(characterId, targetClass)
      .then((res) => {
        if (!cancelled) dispatchPreview({ type: 'finish', key, preview: res.preview });
      })
      .catch((err: unknown) => {
        console.warn('Failed to load level-up preview', err);
        if (!cancelled) dispatchPreview({ type: 'finish', key, preview: null });
      });
    return () => {
      cancelled = true;
    };
  }, [characterId, targetClass]);

  const pendingChoices = (preview?.pending_choices || []) as unknown as CreationChoiceDef[];

  const handleTargetClassChange = (className: string) => {
    dispatchForm({
      type: 'setTargetClass',
      className,
      character,
      spellField: (preview?.spells?.field || 'prepared_spells') as 'prepared_spells' | 'known_spells',
    });
  };

  const addAsi = () => dispatchForm({ type: 'setLocalAsi', value: [...localAsi, { type: 'asi', plus: { str: 2 } }] });
  const addFeat = () => dispatchForm({ type: 'setLocalAsi', value: [...localAsi, { type: 'feat', feat: '' }] });

  const confirm = () => {
    const roll = hpMode === 'average' ? Math.floor(hitDie / 2) + 1 : hpRoll === '' ? undefined : Number(hpRoll);
    const spellPayload: { cantrips?: string[]; prepared_spells?: string[]; known_spells?: string[] } = {};
    if (showCantripPicker) spellPayload.cantrips = localCantrips;
    if (showSpellPicker) spellPayload[spellField] = localSpells;
    onConfirm(roll, localAsi, targetClass, spellPayload, choicePatch);
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
            <ChoiceGroup value={targetClass} onChange={handleTargetClassChange} options={classOptions} columns={2} />
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
            onChange={(v) => dispatchForm({ type: 'setHpMode', mode: v as 'roll' | 'average' })}
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
              onChange={(e) =>
                dispatchForm({ type: 'setHpRoll', value: e.target.value === '' ? '' : parseInt(e.target.value) })
              }
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
              onChange={(value) => dispatchForm({ type: 'setLocalCantrips', value })}
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
              onChange={(value) => dispatchForm({ type: 'setLocalSpells', value })}
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
                        dispatchForm({ type: 'setLocalAsi', value: next });
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
                              dispatchForm({ type: 'setLocalAsi', value: next });
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

        {pendingChoices.length > 0 && (
          <Field label="Class choices at this level">
            <CreationChoicesForm
              char={{ ...character, ...choicePatch }}
              options={options}
              patch={(p) => setChoicePatch((prev) => ({ ...prev, ...p }))}
              choices={pendingChoices}
            />
          </Field>
        )}

        <div className="flex gap-2 justify-end pt-2">
          <button type="button" className="btn-ghost" onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={confirm}
            disabled={loadingPreview || preview?.can_level === false}
          >
            Level up
          </button>
        </div>
      </m.div>
    </div>
  );
}
