import { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import { api } from '../../../api/client';
import type { Character } from '../../../types';
import { spellLimitsFromClass, spellListField } from '../dnd5eCharacterCreation';
import CharacterSheetView from './CharacterSheetView';
import { displayLabel, normalizeChoiceList } from '../../../lib/displayText';
import {
  defaultWizardCharacter,
  WIZARD_STEPS,
  type WizardClassOption,
  type WizardOption,
} from './wizard/wizardConstants';
import WizardBasicsStep from './wizard/WizardBasicsStep';
import WizardOriginStep from './wizard/WizardOriginStep';
import WizardAbilitiesStep from './wizard/WizardAbilitiesStep';
import WizardSkillsSpellsStep from './wizard/WizardSkillsSpellsStep';
import WizardFeaturesStep from './wizard/WizardFeaturesStep';
import WizardStartingGearStep from './wizard/WizardStartingGearStep';
import { validateChoices, choicesForDraft, type CreationChoiceCatalog } from '../../../lib/creationChoices';

interface Props {
  initial?: Character;
  onSave: (char: Character) => void;
  onCancel?: () => void;
}

export default function CharacterWizard({ initial, onSave, onCancel }: Props) {
  const [step, setStep] = useState(0);
  const [options, setOptions] = useState<Record<string, unknown>>({});
  const [previewChar, setPreviewChar] = useState<Character | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [char, setChar] = useReducer(
    (state: Character, patch: Partial<Character>) => ({ ...state, ...patch }),
    initial || (defaultWizardCharacter as Character),
  );

  const patch = (p: Partial<Character>) => setChar(p);

  const classes = (options.classes || []) as WizardClassOption[];
  const species = (options.species || []) as WizardOption[];
  const backgrounds = (options.backgrounds || []) as (WizardOption & { source?: string })[];
  const phbBackgrounds = backgrounds.filter((b) => b.source !== 'faerun');
  const faerunBackgrounds = backgrounds.filter((b) => b.source === 'faerun');
  const skills = (options.skills || []) as { id: string; label: string }[];
  const selectedClass = classes.find((c) => c.id === char.class_name);
  const spellLimits = useMemo(() => spellLimitsFromClass(selectedClass, char.level || 1), [selectedClass, char.level]);
  const spellField = spellListField(selectedClass?.spellcasting);
  const spellLists = useMemo(
    () => (options.spell_lists || {}) as Record<string, Record<string, string[]>>,
    [options.spell_lists],
  );
  const spellList = useMemo(
    () => spellLists[selectedClass?.spell_list || char.class_name || ''] || {},
    [spellLists, selectedClass?.spell_list, char.class_name],
  );

  const spellOptions = useMemo(() => {
    const result: string[] = [];
    for (const [k, arr] of Object.entries(spellList)) {
      if (k !== 'cantrips') result.push(...(arr as string[]));
    }
    return result;
  }, [spellList]);

  const includeFaerun = (char.campaign_setting || defaultWizardCharacter.campaign_setting) === 'faerun';

  useEffect(() => {
    let cancelled = false;
    api.getCharacterOptions(includeFaerun).then((data) => {
      if (!cancelled) setOptions(data);
    });
    return () => {
      cancelled = true;
    };
  }, [includeFaerun]);

  const normalizeSpellFields = useCallback(
    (draft: Character, cls: WizardClassOption | undefined, sl: Record<string, string[]>) => {
      if (!cls || !sl.cantrips) return {};
      const cantrips = normalizeChoiceList(draft.cantrips || [], sl.cantrips || []);
      const prepared = normalizeChoiceList(draft.prepared_spells || [], spellOptions);
      const classSkillOpts = (cls.skill_choices || []) as string[];
      const classSkills = normalizeChoiceList(draft.class_skill_choices || [], classSkillOpts);
      const patchFields: Partial<Character> = {};
      if (JSON.stringify(cantrips) !== JSON.stringify(draft.cantrips)) patchFields.cantrips = cantrips;
      if (JSON.stringify(prepared) !== JSON.stringify(draft.prepared_spells)) patchFields.prepared_spells = prepared;
      if (JSON.stringify(classSkills) !== JSON.stringify(draft.class_skill_choices)) {
        patchFields.class_skill_choices = classSkills;
      }
      return patchFields;
    },
    [spellOptions],
  );

  const startingGearOptions = useMemo(() => {
    const byClass = (options.starting_gear_options || {}) as Record<
      string,
      { id: string; label: string; description?: string }[]
    >;
    return byClass[char.class_name] || [];
  }, [options.starting_gear_options, char.class_name]);

  const backgroundGearOptions = useMemo(() => {
    const byBg = (options.background_starting_gear_options || {}) as Record<
      string,
      { id: string; label: string; description?: string }[]
    >;
    return byBg[char.background] || [];
  }, [options.background_starting_gear_options, char.background]);

  const featureChoiceMissing = useMemo(() => {
    const catalog = (options.creation_choice_catalog || {}) as CreationChoiceCatalog;
    return validateChoices(char, choicesForDraft(char, options, catalog));
  }, [char, options]);

  const patchClassName = (className: string) => {
    const cls = classes.find((c) => c.id === className);
    const sl = spellLists[cls?.spell_list || className] || {};
    const draft = { ...char, class_name: className };
    patch({
      class_name: className,
      starting_gear_choice: '',
      ...normalizeSpellFields(draft, cls, sl),
    });
  };

  const goToStep = async (next: number) => {
    if (next === 3 && selectedClass && spellList.cantrips) {
      const extras = normalizeSpellFields(char, selectedClass, spellList);
      if (Object.keys(extras).length) patch(extras);
    }
    if (next === 5 && startingGearOptions.length > 0 && !char.starting_gear_choice) {
      patch({ starting_gear_choice: startingGearOptions[0].id });
    }
    if (next === 5 && backgroundGearOptions.length > 0 && !char.background_gear_choice) {
      patch({ background_gear_choice: backgroundGearOptions[0].id });
    }
    if (next === 6) {
      setPreviewLoading(true);
      setPreviewChar(null);
      try {
        const { character } = await api.previewCharacter(char as Record<string, unknown>, !initial);
        setPreviewChar(character as Character);
      } catch {
        setPreviewChar(char);
      } finally {
        setPreviewLoading(false);
      }
    }
    setStep(next);
  };

  const applyStandardArray = () => {
    const table = (options.standard_array_by_class || {}) as Record<string, Record<string, number>>;
    const scores = table[char.class_name];
    if (!scores) return;
    patch({
      base_ability_scores: scores,
      ability_scores_set: true,
    });
  };

  const skillOptions = selectedClass?.skill_options;
  const allowedSkillIds = Array.isArray(skillOptions) ? new Set(skillOptions) : null;
  const classSkillOptions = skillOptions === 'any' ? skills : skills.filter((s) => allowedSkillIds?.has(s.id) ?? false);

  const backgroundGroups = [
    {
      label: "Player's Handbook",
      options: phbBackgrounds.map((b) => ({ value: b.id, label: b.label || displayLabel(b.id) })),
    },
    ...(faerunBackgrounds.length
      ? [
          {
            label: 'Heroes of Faerûn',
            options: faerunBackgrounds.map((b) => ({
              value: b.id,
              label: b.label || displayLabel(b.id),
            })),
          },
        ]
      : []),
  ];

  return (
    <div className="panel-glow p-5 md:p-6 space-y-5">
      <div className="flex gap-1 text-xs flex-wrap p-1 rounded-lg bg-bg/50 border border-border w-fit">
        {WIZARD_STEPS.map((s, i) => (
          <span
            key={s}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              i === step ? 'bg-accent/15 text-accent border border-accent/25' : 'text-muted'
            }`}
          >
            {i + 1}. {s}
          </span>
        ))}
      </div>

      <WizardStepBody
        step={step}
        char={char}
        patch={patch}
        onClassChange={patchClassName}
        classes={classes}
        species={species}
        backgroundGroups={backgroundGroups}
        faerunBackgroundIds={faerunBackgrounds.map((b) => b.id)}
        selectedClass={selectedClass}
        classSkillOptions={classSkillOptions}
        spellLimits={spellLimits}
        spellField={spellField}
        spellList={spellList}
        spellOptions={spellOptions}
        options={options}
        startingGearOptions={startingGearOptions}
        backgroundGearOptions={backgroundGearOptions}
        previewLoading={previewLoading}
        previewChar={previewChar}
        onApplyStandardArray={applyStandardArray}
      />
      <WizardNav
        step={step}
        featureChoiceMissing={featureChoiceMissing.length}
        startingGearOptions={startingGearOptions}
        backgroundGearOptions={backgroundGearOptions}
        char={char}
        previewChar={previewChar}
        onCancel={onCancel}
        onGoToStep={goToStep}
        onSave={onSave}
      />
    </div>
  );
}

function WizardStepBody({
  step,
  char,
  patch,
  onClassChange,
  classes,
  species,
  backgroundGroups,
  faerunBackgroundIds,
  selectedClass,
  classSkillOptions,
  spellLimits,
  spellField,
  spellList,
  spellOptions,
  options,
  startingGearOptions,
  backgroundGearOptions,
  previewLoading,
  previewChar,
  onApplyStandardArray,
}: {
  step: number;
  char: Character;
  patch: (p: Partial<Character>) => void;
  onClassChange: (className: string) => void;
  classes: WizardClassOption[];
  species: WizardOption[];
  backgroundGroups: { label: string; options: { value: string; label: string }[] }[];
  faerunBackgroundIds: string[];
  selectedClass: WizardClassOption | undefined;
  classSkillOptions: { id: string; label: string }[];
  spellLimits: ReturnType<typeof spellLimitsFromClass>;
  spellField: ReturnType<typeof spellListField>;
  spellList: Record<string, string[]>;
  spellOptions: string[];
  options: Record<string, unknown>;
  startingGearOptions: { id: string; label: string; description?: string }[];
  backgroundGearOptions: { id: string; label: string; description?: string }[];
  previewLoading: boolean;
  previewChar: Character | null;
  onApplyStandardArray: () => void;
}) {
  if (step === 0) {
    return (
      <WizardBasicsStep
        char={char}
        patch={patch}
        onClassChange={onClassChange}
        onCampaignSettingChange={(_setting, patchFields) => {
          patch(patchFields);
        }}
        classes={classes}
        species={species}
        backgroundGroups={backgroundGroups}
        faerunBackgroundIds={faerunBackgroundIds}
      />
    );
  }
  if (step === 1) return <WizardOriginStep char={char} patch={patch} />;
  if (step === 2) return <WizardAbilitiesStep char={char} patch={patch} onApplyStandardArray={onApplyStandardArray} />;
  if (step === 3) {
    return (
      <WizardSkillsSpellsStep
        char={char}
        patch={patch}
        selectedClass={selectedClass}
        classSkillOptions={classSkillOptions}
        spellLimits={spellLimits}
        spellField={spellField}
        spellList={spellList}
        spellOptions={spellOptions}
      />
    );
  }
  if (step === 4) return <WizardFeaturesStep char={char} options={options} patch={patch} />;
  if (step === 5) {
    return (
      <WizardStartingGearStep
        char={char}
        classOptions={startingGearOptions}
        backgroundOptions={backgroundGearOptions}
        patch={patch}
      />
    );
  }
  if (previewLoading) {
    return <p className="text-sm text-muted py-8 text-center">Building character preview…</p>;
  }
  return <CharacterSheetView character={previewChar || char} />;
}

function WizardNav({
  step,
  featureChoiceMissing,
  startingGearOptions,
  backgroundGearOptions,
  char,
  previewChar,
  onCancel,
  onGoToStep,
  onSave,
}: {
  step: number;
  featureChoiceMissing: number;
  startingGearOptions: { id: string }[];
  backgroundGearOptions: { id: string }[];
  char: Character;
  previewChar: Character | null;
  onCancel?: () => void;
  onGoToStep: (next: number) => void;
  onSave: (char: Character) => void;
}) {
  const nextDisabled =
    (step === 4 && featureChoiceMissing > 0) ||
    (step === 5 && startingGearOptions.length > 1 && !char.starting_gear_choice) ||
    (step === 5 && Boolean(char.background) && backgroundGearOptions.length > 1 && !char.background_gear_choice);
  const isLast = step >= WIZARD_STEPS.length - 1;
  return (
    <div className="flex gap-2 justify-between pt-2">
      <div>
        {onCancel && (
          <button type="button" className="btn-ghost" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
      <div className="flex gap-2">
        {step > 0 && (
          <button type="button" className="btn-ghost" onClick={() => onGoToStep(step - 1)}>
            Back
          </button>
        )}
        {isLast ? (
          <button type="button" className="btn-primary" onClick={() => onSave((previewChar || char) as Character)}>
            Save character
          </button>
        ) : (
          <button type="button" className="btn-primary" onClick={() => onGoToStep(step + 1)} disabled={nextDisabled}>
            Next
          </button>
        )}
      </div>
    </div>
  );
}
