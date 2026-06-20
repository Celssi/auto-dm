import { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import { api } from '../../api/client';
import type { Character } from '../../types';
import { spellLimitsFromClass, spellListField } from '../../lib/dnd5eCharacterCreation';
import CharacterSheetView from './CharacterSheetView';
import { displayLabel, normalizeChoiceList } from '../../lib/displayText';
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

interface Props {
  initial?: Character;
  onSave: (char: Character) => void;
  onCancel?: () => void;
}

export default function CharacterWizard({ initial, onSave, onCancel }: Props) {
  const [step, setStep] = useState(0);
  const [options, setOptions] = useState<Record<string, unknown>>({});
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

  const patchClassName = (className: string) => {
    const cls = classes.find((c) => c.id === className);
    const sl = spellLists[cls?.spell_list || className] || {};
    const draft = { ...char, class_name: className };
    patch({ class_name: className, ...normalizeSpellFields(draft, cls, sl) });
  };

  const goToStep = (next: number) => {
    if (next === 3 && selectedClass && spellList.cantrips) {
      const extras = normalizeSpellFields(char, selectedClass, spellList);
      if (Object.keys(extras).length) patch(extras);
    }
    setStep(next);
  };

  const applyStandardArray = () => {
    const table = (options.standard_array_by_class || {}) as Record<string, Record<string, number>>;
    const scores = table[char.class_name];
    if (!scores) return;
    patch({
      base_ability_scores: scores,
      ability_scores: scores,
      ability_scores_set: true,
    });
  };

  const classSkillOptions =
    selectedClass?.skill_options === 'any'
      ? skills
      : skills.filter((s) => (selectedClass?.skill_options as string[] | undefined)?.includes(s.id));

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

      {step === 0 && (
        <WizardBasicsStep
          char={char}
          patch={patch}
          onClassChange={patchClassName}
          onCampaignSettingChange={(_setting, patchFields) => {
            patch(patchFields);
          }}
          classes={classes}
          species={species}
          backgroundGroups={backgroundGroups}
          faerunBackgroundIds={faerunBackgrounds.map((b) => b.id)}
        />
      )}
      {step === 1 && <WizardOriginStep char={char} patch={patch} />}
      {step === 2 && <WizardAbilitiesStep char={char} patch={patch} onApplyStandardArray={applyStandardArray} />}
      {step === 3 && (
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
      )}
      {step === 4 && <CharacterSheetView character={char} />}

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
            <button type="button" className="btn-ghost" onClick={() => goToStep(step - 1)}>
              Back
            </button>
          )}
          {step < WIZARD_STEPS.length - 1 ? (
            <button type="button" className="btn-primary" onClick={() => goToStep(step + 1)}>
              Next
            </button>
          ) : (
            <button type="button" className="btn-primary" onClick={() => onSave(char)}>
              Save character
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
