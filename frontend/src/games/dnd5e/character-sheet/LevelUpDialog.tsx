import { useEffect, useReducer, useState, type Dispatch, type SetStateAction } from 'react';
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
    localAsi: ((character.asi_choices || []) as Record<string, unknown>[]).map(withAsiId),
    localCantrips: character.cantrips || [],
    localSpells: spellValuesForField(character, spellField),
  };
}

function withAsiId(choice: Record<string, unknown>): Record<string, unknown> {
  return typeof choice.uiId === 'string' ? choice : { ...choice, uiId: crypto.randomUUID() };
}

function asiPayload(choices: Record<string, unknown>[]): Record<string, unknown>[] {
  return choices.map(({ uiId: _uiId, ...rest }) => rest);
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

function spellPickerVisible(
  hasOptions: boolean,
  budget: { additional_picks: number; limit_increased?: boolean } | undefined,
) {
  return Boolean(hasOptions && budget && (budget.additional_picks > 0 || budget.limit_increased));
}

function confirmLevelUpArgs({
  hpMode,
  hpRoll,
  hitDie,
  showCantripPicker,
  showSpellPicker,
  localCantrips,
  localSpells,
  spellField,
  localAsi,
  targetClass,
  choicePatch,
}: {
  hpMode: 'roll' | 'average';
  hpRoll: number | '';
  hitDie: number;
  showCantripPicker: boolean;
  showSpellPicker: boolean;
  localCantrips: string[];
  localSpells: string[];
  spellField: 'prepared_spells' | 'known_spells';
  localAsi: Record<string, unknown>[];
  targetClass: string;
  choicePatch: Partial<Character>;
}): Parameters<Props['onConfirm']> {
  const roll = hpMode === 'average' ? Math.floor(hitDie / 2) + 1 : hpRoll === '' ? undefined : Number(hpRoll);
  const spellPayload: { cantrips?: string[]; prepared_spells?: string[]; known_spells?: string[] } = {};
  if (showCantripPicker) spellPayload.cantrips = localCantrips;
  if (showSpellPicker) spellPayload[spellField] = localSpells;
  return [roll, asiPayload(localAsi), targetClass, spellPayload, choicePatch];
}

function levelUpClassEntries(character: Character, summary: Summary) {
  return (
    summary.classes?.length ? summary.classes : [{ class_name: character.class_name, level: character.level }]
  ) as ClassLevel[];
}

function levelUpDerived(
  characterId: string,
  character: Character,
  summary: Summary,
  classEntries: ClassLevel[],
  form: FormState,
  previewState: PreviewState,
) {
  const preview = previewState.preview;
  const spellField = (preview?.spells?.field || 'prepared_spells') as 'prepared_spells' | 'known_spells';
  const cantripBudget = preview?.cantrips;
  const spellBudget = preview?.spells;
  return {
    selected: classEntries.find((c) => c.class_name === form.targetClass) || classEntries[0],
    preview,
    loadingPreview: previewState.loading,
    hitDie: preview?.hit_die || summary.hit_die || character.hit_die || 8,
    spellField,
    formKey: `${characterId}:${form.targetClass}:${spellField}`,
    showAsi: Boolean(summary.needs_asi || preview?.asi_this_level),
    cantripBudget,
    spellBudget,
    showCantripPicker: spellPickerVisible(Boolean(preview?.spell_list?.cantrips?.length), cantripBudget),
    showSpellPicker: spellPickerVisible(Boolean(preview?.spell_list?.options?.length), spellBudget),
  };
}

export default function LevelUpDialog({ characterId, character, summary, onConfirm, onCancel }: Props) {
  const classEntries = levelUpClassEntries(character, summary);
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
  const derived = levelUpDerived(characterId, character, summary, classEntries, form, previewState);
  const {
    selected,
    preview,
    loadingPreview,
    hitDie,
    spellField,
    showAsi,
    cantripBudget,
    spellBudget,
    showCantripPicker,
    showSpellPicker,
  } = derived;

  if (derived.formKey !== form.key) {
    dispatchForm({ type: 'reset', key: derived.formKey, character, spellField });
  }

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

  const addAsi = () =>
    dispatchForm({
      type: 'setLocalAsi',
      value: [...localAsi, withAsiId({ type: 'asi', plus: { str: 2 } })],
    });
  const addFeat = () =>
    dispatchForm({ type: 'setLocalAsi', value: [...localAsi, withAsiId({ type: 'feat', feat: '' })] });

  const confirm = () =>
    onConfirm(
      ...confirmLevelUpArgs({
        hpMode,
        hpRoll,
        hitDie,
        showCantripPicker,
        showSpellPicker,
        localCantrips,
        localSpells,
        spellField,
        localAsi,
        targetClass,
        choicePatch,
      }),
    );

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

        <LevelUpFields
          classEntries={classEntries}
          targetClass={targetClass}
          classOptions={classOptions}
          onTargetClassChange={handleTargetClassChange}
          loadingPreview={loadingPreview}
          preview={preview}
          hitDie={hitDie}
          selected={selected}
          character={character}
          hpMode={hpMode}
          hpRoll={hpRoll}
          dispatchForm={dispatchForm}
          showCantripPicker={showCantripPicker}
          cantripBudget={cantripBudget}
          localCantrips={localCantrips}
          showSpellPicker={showSpellPicker}
          spellBudget={spellBudget}
          localSpells={localSpells}
          showAsi={showAsi}
          summary={summary}
          localAsi={localAsi}
          addAsi={addAsi}
          addFeat={addFeat}
          pendingChoices={pendingChoices}
          options={options}
          choicePatch={choicePatch}
          setChoicePatch={setChoicePatch}
        />

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

function LevelUpFields({
  classEntries,
  targetClass,
  classOptions,
  onTargetClassChange,
  loadingPreview,
  preview,
  hitDie,
  selected,
  character,
  hpMode,
  hpRoll,
  dispatchForm,
  showCantripPicker,
  cantripBudget,
  localCantrips,
  showSpellPicker,
  spellBudget,
  localSpells,
  showAsi,
  summary,
  localAsi,
  addAsi,
  addFeat,
  pendingChoices,
  options,
  choicePatch,
  setChoicePatch,
}: {
  classEntries: ClassLevel[];
  targetClass: string;
  classOptions: { value: string; label: string }[];
  onTargetClassChange: (className: string) => void;
  loadingPreview: boolean;
  preview: LevelUpPreview | null;
  hitDie: number;
  selected: ClassLevel | undefined;
  character: Character;
  hpMode: 'roll' | 'average';
  hpRoll: number | '';
  dispatchForm: Dispatch<FormAction>;
  showCantripPicker: boolean;
  cantripBudget: LevelUpPreview['cantrips'];
  localCantrips: string[];
  showSpellPicker: boolean;
  spellBudget: LevelUpPreview['spells'];
  localSpells: string[];
  showAsi: boolean;
  summary: Summary;
  localAsi: Record<string, unknown>[];
  addAsi: () => void;
  addFeat: () => void;
  pendingChoices: CreationChoiceDef[];
  options: Record<string, unknown>;
  choicePatch: Partial<Character>;
  setChoicePatch: Dispatch<SetStateAction<Partial<Character>>>;
}) {
  return (
    <>
      {classEntries.length > 1 && (
        <Field label="Which class gains a level?">
          <ChoiceGroup value={targetClass} onChange={onTargetClassChange} options={classOptions} columns={2} />
        </Field>
      )}
      {loadingPreview && <p className="text-xs text-muted">Loading level-up changes…</p>}
      <LevelUpNotices preview={preview} loadingPreview={loadingPreview} />
      <LevelUpHpField
        hitDie={hitDie}
        className={selected?.class_name || character.class_name}
        hpMode={hpMode}
        hpRoll={hpRoll}
        dispatchForm={dispatchForm}
      />
      {showCantripPicker && cantripBudget && (
        <LevelUpSpellPicker
          label={`Cantrips (max ${cantripBudget.limit_after}${cantripBudget.additional_picks ? `: pick ${cantripBudget.additional_picks} more` : ''})`}
          budget={cantripBudget}
          value={localCantrips}
          options={preview?.spell_list?.cantrips || []}
          extraNote
          onChange={(value) => dispatchForm({ type: 'setLocalCantrips', value })}
        />
      )}
      {showSpellPicker && spellBudget && (
        <LevelUpSpellPicker
          label={`${spellBudget.label} (max ${spellBudget.limit_after}${spellBudget.additional_picks ? `: pick ${spellBudget.additional_picks} more` : ''})`}
          budget={spellBudget}
          value={localSpells}
          options={preview?.spell_list?.options || []}
          onChange={(value) => dispatchForm({ type: 'setLocalSpells', value })}
        />
      )}
      {showAsi && (
        <LevelUpAsiField
          summary={summary}
          preview={preview}
          localAsi={localAsi}
          dispatchForm={dispatchForm}
          addAsi={addAsi}
          addFeat={addFeat}
        />
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
    </>
  );
}

function LevelUpNotices({ preview, loadingPreview }: { preview: LevelUpPreview | null; loadingPreview: boolean }) {
  return (
    <>
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
    </>
  );
}

function LevelUpHpField({
  hitDie,
  className,
  hpMode,
  hpRoll,
  dispatchForm,
}: {
  hitDie: number;
  className: string;
  hpMode: 'roll' | 'average';
  hpRoll: number | '';
  dispatchForm: Dispatch<FormAction>;
}) {
  return (
    <Field label={`Hit Points (d${hitDie} + CON), ${displayLabel(className)}`}>
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
  );
}

function LevelUpSpellPicker({
  label,
  budget,
  value,
  options,
  extraNote,
  onChange,
}: {
  label: string;
  budget: { additional_picks: number; limit_increased?: boolean; limit_after: number; current: number };
  value: string[];
  options: string[];
  extraNote?: boolean;
  onChange: (value: string[]) => void;
}) {
  return (
    <Field label={label}>
      {budget.additional_picks === 0 && budget.limit_increased && (
        <p className="text-xs text-muted mb-2">
          Limit increases to {budget.limit_after}; you already have {budget.current}
          {extraNote ? '. No new picks required.' : '.'}
        </p>
      )}
      <MultiChoice value={value} onChange={onChange} options={options} max={budget.limit_after} />
    </Field>
  );
}

function LevelUpAsiField({
  summary,
  preview,
  localAsi,
  dispatchForm,
  addAsi,
  addFeat,
}: {
  summary: Summary;
  preview: LevelUpPreview | null;
  localAsi: Record<string, unknown>[];
  dispatchForm: Dispatch<FormAction>;
  addAsi: () => void;
  addFeat: () => void;
}) {
  return (
    <Field label={`ASI / Feat (${summary.asi_feat_taken}/${summary.asi_feat_slots} taken)`}>
      {preview?.asi_this_level && (
        <p className="text-xs text-muted mb-2">This level grants an Ability Score Improvement or feat.</p>
      )}
      <div className="space-y-3 max-h-48 overflow-y-auto">
        {localAsi.map((choice, i) => (
          <LevelUpAsiChoice
            key={String(choice.uiId)}
            choice={choice}
            onChange={(next) => {
              const copy = [...localAsi];
              copy[i] = next;
              dispatchForm({ type: 'setLocalAsi', value: copy });
            }}
          />
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
  );
}

function LevelUpAsiChoice({
  choice,
  onChange,
}: {
  choice: Record<string, unknown>;
  onChange: (choice: Record<string, unknown>) => void;
}) {
  if (choice.type === 'feat') {
    return (
      <div className="text-xs border border-border rounded-lg p-3 bg-bg/30">
        <TextInput
          inputClassName="text-xs"
          placeholder="Feat name"
          value={String(choice.feat || '')}
          onChange={(e) => onChange({ ...choice, feat: e.target.value })}
        />
      </div>
    );
  }
  return (
    <div className="text-xs border border-border rounded-lg p-3 bg-bg/30">
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
                const plus = { ...(choice.plus as Record<string, number>) };
                plus[ab] = n;
                onChange({ ...choice, plus });
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
