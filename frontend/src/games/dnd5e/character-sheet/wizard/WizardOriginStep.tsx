import type { Character } from '../../../../types';
import { Field } from '../../../../components/ui/forms/Field';
import TextInput from '../../../../components/ui/forms/TextInput';
import TextArea from '../../../../components/ui/forms/TextArea';
import MultiChoice from '../../../../components/ui/forms/MultiChoice';
import { displayLabel } from '../../../../lib/displayText';

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
  languageOptions: string[];
}

export default function WizardOriginStep({ char, patch, languageOptions }: Props) {
  const appearance = String(char.appearance || char.equipment_notes || '');
  const fc = { ...((char.feature_choices || {}) as Record<string, unknown>) };
  const originLanguages = Array.isArray(fc.origin_languages) ? (fc.origin_languages as string[]) : [];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Alignment">
          <TextInput
            value={char.alignment}
            onChange={(e) => patch({ alignment: e.target.value })}
            placeholder="e.g. Neutral Good"
          />
        </Field>
        <Field label="Campaign notes">
          <TextInput
            value={char.campaign_notes}
            onChange={(e) => patch({ campaign_notes: e.target.value })}
            placeholder="Optional notes"
          />
        </Field>
      </div>
      <Field
        label="Origin languages (pick 2)"
        hint="You know Common. Choose two more Standard Languages. Species does not add a language automatically."
      >
        <MultiChoice
          value={originLanguages}
          onChange={(next) => patch({ feature_choices: { ...fc, origin_languages: next } })}
          options={languageOptions}
          max={2}
          searchable={languageOptions.length > 12}
        />
      </Field>
      {originLanguages.length > 0 && (
        <p className="text-xs text-muted -mt-2">
          Known: Common, {originLanguages.map((id) => displayLabel(id)).join(', ')}
        </p>
      )}
      <Field label="Appearance & Notes">
        <TextArea
          value={appearance}
          onChange={(e) => patch({ appearance: e.target.value, equipment_notes: e.target.value })}
          placeholder="Appearance, personality, backstory, or other notes for the DM"
          className="min-h-[10rem]"
        />
      </Field>
    </div>
  );
}
