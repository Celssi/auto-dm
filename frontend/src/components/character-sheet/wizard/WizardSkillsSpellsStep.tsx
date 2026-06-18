import type { Character } from '../../../types';
import { spellPickLabel } from '../../../lib/dnd5eCharacterCreation';
import { displayLabel } from '../../../lib/displayText';
import { Field } from '../../ui/forms/Field';
import MultiChoice from '../../ui/forms/MultiChoice';
import GlossaryTip from '../../ui/GlossaryTip';
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
  onToggleSkill: (id: string) => void;
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
  onToggleSkill,
}: Props) {
  return (
    <div className="space-y-5">
      {selectedClass && (selectedClass.skill_choices || 0) > 0 && (
        <Field label={`Class skills (pick ${selectedClass.skill_choices})`}>
          <div className="flex flex-wrap gap-1.5">
            {classSkillOptions.map((sk) => {
              const picked = ((char.class_skill_choices || []) as string[]).includes(sk.id);
              return (
                <GlossaryTip key={sk.id} name={sk.id} variant="custom">
                  <button
                    type="button"
                    className={`text-xs px-2.5 py-1.5 rounded-full border transition-colors cursor-help ${
                      picked
                        ? 'border-accent/50 bg-accent/15 text-accent'
                        : 'border-border bg-bg/40 text-gray-300 hover:border-accent/30'
                    }`}
                    onClick={() => onToggleSkill(sk.id)}
                  >
                    {displayLabel(sk.label)}
                  </button>
                </GlossaryTip>
              );
            })}
          </div>
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
