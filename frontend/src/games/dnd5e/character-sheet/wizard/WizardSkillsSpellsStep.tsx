import type { Character } from '../../../../types';
import { spellPickLabel } from '../../dnd5eCharacterCreation';
import { Field } from '../../../../components/ui/forms/Field';
import MultiChoice from '../../../../components/ui/forms/MultiChoice';
import type { WizardClassOption } from './wizardConstants';
import CreationChoicesForm from '../CreationChoicesForm';
import { choicesForDraft, type CreationChoiceCatalog } from '../../../../lib/creationChoices';

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
  selectedClass?: WizardClassOption;
  classSkillOptions: { id: string; label: string }[];
  spellLimits: { cantrips: number; known: number; prepared: number; spellbook?: number };
  spellField: 'known_spells' | 'prepared_spells';
  spellList: Record<string, string[]>;
  spellOptions: string[];
  options?: Record<string, unknown>;
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
  options = {},
}: Props) {
  const isWizard = selectedClass?.id === 'wizard';
  const spellbookMax = Number(spellLimits.spellbook || 0);
  const preparedMax = spellLimits[spellField === 'known_spells' ? 'known' : 'prepared'];
  const preparedOptions = isWizard && (char.spellbook || []).length ? char.spellbook || [] : spellOptions;
  const catalog = (options.creation_choice_catalog || {}) as CreationChoiceCatalog;
  const magicInitiateChoices = choicesForDraft(char, options, catalog).filter((choice) =>
    String(choice.id || '').startsWith('magic_initiate'),
  );

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
          {spellLimits.cantrips > 0 && (
            <Field label={`Cantrips (max ${spellLimits.cantrips})`}>
              <MultiChoice
                value={char.cantrips}
                onChange={(cantrips) => patch({ cantrips })}
                options={spellList.cantrips || []}
                max={spellLimits.cantrips}
              />
            </Field>
          )}
          {isWizard && spellbookMax > 0 && (
            <Field
              label={`Spellbook (pick ${spellbookMax} level 1 wizard spells)`}
              hint="You copy these into your book. Prepare a subset below. Ritual Adept uses the book, not prepared spells."
            >
              <MultiChoice
                value={char.spellbook || []}
                onChange={(picks) => {
                  const nextBook = picks.slice(0, spellbookMax);
                  const prepared = ((char.prepared_spells || []) as string[]).filter((name) => nextBook.includes(name));
                  patch({ spellbook: nextBook, prepared_spells: prepared });
                }}
                options={spellOptions}
                max={spellbookMax}
                searchable
              />
            </Field>
          )}
          {preparedMax > 0 && (
            <Field
              label={`${spellPickLabel(selectedClass.spellcasting)} (max ${preparedMax})`}
              hint={isWizard ? 'Choose from your spellbook.' : undefined}
            >
              <MultiChoice
                value={(char[spellField] as string[]) || []}
                onChange={(picks) => patch({ [spellField]: picks })}
                options={preparedOptions}
                max={preparedMax}
                searchable={preparedOptions.length > 12}
              />
            </Field>
          )}
        </>
      )}
      {magicInitiateChoices.length > 0 && (
        <div className="space-y-3 rounded-lg border border-border p-4">
          <p className="text-sm text-muted leading-relaxed">
            Sage and other Magic Initiate backgrounds pick two cantrips and one 1st-level spell here. You can cast the
            1st-level spell once per Long Rest without a slot.
          </p>
          <CreationChoicesForm char={char} options={options} patch={patch} choices={magicInitiateChoices} />
        </div>
      )}
    </div>
  );
}
