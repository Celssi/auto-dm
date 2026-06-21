import type { Character } from '../../../types';
import { Field } from '../../ui/forms/Field';
import TextInput from '../../ui/forms/TextInput';
import TextArea from '../../ui/forms/TextArea';

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
}

export default function WizardOriginStep({ char, patch }: Props) {
  const appearance = String(char.appearance || char.equipment_notes || '');

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
