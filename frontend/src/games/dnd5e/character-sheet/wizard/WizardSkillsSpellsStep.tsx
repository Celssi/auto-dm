import type { Character } from '../../../../types';
import { spellPickLabel } from '../../dnd5eCharacterCreation';
import { Field } from '../../../../components/ui/forms/Field';
import MultiChoice from '../../../../components/ui/forms/MultiChoice';
import type { WizardClassOption } from './wizardConstants';

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
  selectedClass?: WizardClassOption;
  classSkillOptions: { id: string; label: string }[];
  spellLimits: { cantrips: number; known: number; prepared: number };
  spellField: 'known_spells' | 'prepared_spells';
  spellList: Record<string, string[]>;
  spellOptions: string[];
}

export default function WizardSkillsSpellsStep({
  char,
  patch,
  selectedClass,
  classSkillOptions,
  spellLimits,
  spellField,
  spellList,
  spellOptions,
}: Props) {
  return (
    <div className="space-y-5">
      {selectedClass && (selectedClass.skill_choices || 0) > 0 && (
        <Field label={`Class skills (pick ${selectedClass.skill_choices})`}>
          <MultiChoice
            value={(char.class_skill_choices || []) as string[]}
            onChange={(next) => patch({ class_skill_choices: next })}
            options={classSkillOptions.map((sk) => sk.id)}
            max={selectedClass.skill_choices}
            searchable={classSkillOptions.length > 12}
          />
        </Field>
      )}
      {selectedClass?.spellcasting && (
        <>
          <Field label={`Cantrips (max ${spellLimits.cantrips})`}>
            <MultiChoice
              value={char.cantrips}
              onChange={(cantrips) => patch({ cantrips })}
              options={spellList.cantrips || []}
              max={spellLimits.cantrips}
            />
          </Field>
          <Field
            label={`${spellPickLabel(selectedClass.spellcasting)} (max ${
              spellLimits[spellField === 'known_spells' ? 'known' : 'prepared']
            })`}
          >
            <MultiChoice
              value={(char[spellField] as string[]) || []}
              onChange={(picks) => patch({ [spellField]: picks })}
              options={spellOptions}
              max={spellLimits[spellField === 'known_spells' ? 'known' : 'prepared']}
            />
          </Field>
        </>
      )}
    </div>
  );
}
