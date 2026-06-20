import type { Character } from '../../../types';
import { Field } from '../../ui/forms/Field';
import TextInput from '../../ui/forms/TextInput';
import ChoiceGroup from '../../ui/forms/ChoiceGroup';
import SegmentedControl from '../../ui/forms/SegmentedControl';
import { displayLabel } from '../../../lib/displayText';
import type { WizardClassOption, WizardOption } from './wizardConstants';

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
  onClassChange: (className: string) => void;
  onCampaignSettingChange: (setting: string, patchFields: Partial<Character>) => void;
  classes: WizardClassOption[];
  species: WizardOption[];
  backgroundGroups: { label: string; options: { value: string; label: string }[] }[];
  faerunBackgroundIds: string[];
}

export default function WizardBasicsStep({
  char,
  patch,
  onClassChange,
  onCampaignSettingChange,
  classes,
  species,
  backgroundGroups,
  faerunBackgroundIds,
}: Props) {
  return (
    <div className="space-y-5">
      <Field label="Campaign setting">
        <SegmentedControl
          value={char.campaign_setting || 'freeform'}
          onChange={(setting) => {
            const isFaerunBg = faerunBackgroundIds.includes(char.background);
            onCampaignSettingChange(setting, {
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
        <p className="text-xs text-muted leading-relaxed -mt-2">
          Faerûn backgrounds and subclasses from Heroes of Faerûn are available below.
        </p>
      )}
      <Field label="Name">
        <TextInput value={char.name} onChange={(e) => patch({ name: e.target.value })} placeholder="Character name" />
      </Field>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <Field label="Class">
          <ChoiceGroup
            value={char.class_name}
            onChange={onClassChange}
            options={classes.map((c) => ({
              value: c.id,
              label: c.label || displayLabel(c.id),
            }))}
            allowEmpty
            columns={2}
          />
        </Field>
        <Field label="Species">
          <ChoiceGroup
            value={char.species}
            onChange={(v) => patch({ species: v })}
            options={species.map((s) => ({
              value: s.id,
              label: s.label || displayLabel(s.id),
            }))}
            allowEmpty
            columns={2}
          />
        </Field>
      </div>
      <Field label="Background">
        <ChoiceGroup
          value={char.background}
          onChange={(v) => patch({ background: v })}
          groups={backgroundGroups}
          allowEmpty
          columns={2}
        />
      </Field>
    </div>
  );
}
