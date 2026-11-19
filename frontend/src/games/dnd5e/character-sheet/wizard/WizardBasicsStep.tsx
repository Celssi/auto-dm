import type { Character } from '../../../../types';
import { Field } from '../../../../components/ui/forms/Field';
import TextInput from '../../../../components/ui/forms/TextInput';
import ChoiceGroup from '../../../../components/ui/forms/ChoiceGroup';
import SegmentedControl from '../../../../components/ui/forms/SegmentedControl';
import { displayLabel } from '../../../../lib/displayText';
import { BACKGROUND_BLURBS, CLASS_BLURBS, type WizardClassOption, type WizardOption } from './wizardConstants';

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
  onClassChange: (className: string) => void;
  onCampaignSettingChange: (setting: string, patchFields: Partial<Character>) => void;
  classes: WizardClassOption[];
  species: WizardOption[];
  backgroundGroups: { label: string; options: { value: string; label: string }[] }[];
  backgrounds: WizardOption[];
  faerunBackgroundIds: string[];
}

function featForBackground(backgrounds: WizardOption[], id: string): string {
  const row = backgrounds.find((b) => b.id === id);
  return String(row?.feat || '');
}

export default function WizardBasicsStep({
  char,
  patch,
  onClassChange,
  onCampaignSettingChange,
  classes,
  species,
  backgroundGroups,
  backgrounds,
  faerunBackgroundIds,
}: Props) {
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted leading-relaxed">
        This wizard uses D&D 5e 2024 rules only, not the 2014 rulebooks. Dotted labels on the finished sheet explain
        Armor Class, Exhaustion, Heroic Inspiration, and Weapon Mastery.
      </p>
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
              description: CLASS_BLURBS[c.id],
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
          onChange={(v) => {
            patch({
              background: v,
              origin_feat: featForBackground(backgrounds, v),
              background_asi_plus2: '',
              background_asi_plus1: '',
              background_asi_all_three: false,
            });
          }}
          groups={backgroundGroups.map((group) => ({
            ...group,
            options: group.options.map((opt) => ({
              ...opt,
              description: BACKGROUND_BLURBS[opt.value],
            })),
          }))}
          allowEmpty
          columns={2}
        />
      </Field>
    </div>
  );
}
