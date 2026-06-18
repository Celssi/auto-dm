import type { Character } from '../../../types';
import { Field } from '../../ui/forms/Field';
import TextInput from '../../ui/forms/TextInput';
import SegmentedControl from '../../ui/forms/SegmentedControl';

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
  faerunBackgroundIds: string[];
}

export default function WizardOriginStep({ char, patch, faerunBackgroundIds }: Props) {
  return (
    <div className="space-y-5">
      <Field label="Campaign setting">
        <SegmentedControl
          value={char.campaign_setting || 'freeform'}
          onChange={(setting) => {
            const isFaerunBg = faerunBackgroundIds.includes(char.background);
            patch({
              campaign_setting: setting,
              ...(setting !== 'faerun' && isFaerunBg ? { background: '' } : {}),
            });
          }}
          options={[
            { value: 'freeform', label: 'Freeform' },
            { value: 'faerun', label: 'Faerûn' },
          ]}
        />
      </Field>
      {char.campaign_setting === 'faerun' && (
        <p className="text-xs text-muted leading-relaxed">
          Faerûn backgrounds and subclasses from Heroes of Faerûn are available. Spell and feat details can also be
          looked up via rules search.
        </p>
      )}
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
    </div>
  );
}
