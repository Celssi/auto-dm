import type { Character } from '../../types';
import { Field } from '../ui/forms/Field';
import ChoiceGroup from '../ui/forms/ChoiceGroup';
import MultiChoice from '../ui/forms/MultiChoice';
import { displayLabel } from '../../lib/displayText';
import {
  choicesForDraft,
  getChoiceValue,
  patchChoice,
  type CreationChoiceCatalog,
  type CreationChoiceDef,
} from '../../lib/creationChoices';

interface Props {
  char: Character;
  options: Record<string, unknown>;
  patch: (p: Partial<Character>) => void;
  choices?: CreationChoiceDef[];
}

export default function CreationChoicesForm({ char, options, patch, choices }: Props) {
  const catalog = (options.creation_choice_catalog || {}) as CreationChoiceCatalog;
  const resolved = choices || choicesForDraft(char, options, catalog);

  if (resolved.length === 0) {
    return <p className="text-sm text-muted">No additional choices for this character.</p>;
  }

  const setChoice = (choiceId: string, value: unknown) => {
    patch(patchChoice(char, choiceId, value));
  };

  return (
    <div className="space-y-5">
      {resolved.map((choice) => {
        const val = getChoiceValue(char, choice.id);
        const count = Number(choice.count || 1);
        const rawOpts = Array.isArray(choice.options) ? choice.options : [];
        const opts = rawOpts.map((o) => ({
          value: o.id,
          label: o.label || displayLabel(o.id),
        }));

        if (choice.kind === 'weapons' || choice.id === 'weapon_mastery') {
          return (
            <Field key={choice.id} label={`${choice.label} (pick ${count})`} hint={choice.help}>
              <MultiChoice
                value={(val as string[]) || []}
                onChange={(v) => setChoice(choice.id, v.slice(0, count))}
                options={opts.map((o) => o.value)}
                max={count}
              />
            </Field>
          );
        }

        if (choice.kind === 'skills' || choice.kind === 'spells' || choice.kind === 'invocations') {
          const pickOpts =
            choice.kind === 'spells' && choice.spell_options?.length
              ? choice.spell_options.map(String)
              : opts.map((o) => o.value);
          return (
            <Field key={choice.id} label={`${choice.label} (pick ${count})`} hint={choice.help}>
              <MultiChoice
                value={(val as string[]) || []}
                onChange={(v) => setChoice(choice.id, v.slice(0, count))}
                options={pickOpts}
                max={count}
              />
            </Field>
          );
        }

        if (choice.kind === 'spell') {
          const spellOpts = (choice.spell_options || []).map((s) => ({
            value: String(s),
            label: displayLabel(String(s)),
          }));
          return (
            <Field key={choice.id} label={choice.label} hint={choice.help}>
              <ChoiceGroup
                value={String(val || '')}
                onChange={(v) => setChoice(choice.id, v)}
                options={spellOpts}
                allowEmpty
                columns={2}
              />
            </Field>
          );
        }

        return (
          <Field key={choice.id} label={choice.label} hint={choice.help}>
            <ChoiceGroup
              value={String(val || '')}
              onChange={(v) => setChoice(choice.id, v)}
              options={opts}
              allowEmpty
              columns={2}
            />
          </Field>
        );
      })}
    </div>
  );
}
