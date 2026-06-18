import type { Character } from '../../../types';
import { Field } from '../../ui/forms/Field';
import TextInput from '../../ui/forms/TextInput';
import ChoiceGroup from '../../ui/forms/ChoiceGroup';
import { displayLabel } from '../../../lib/displayText';
import type { WizardClassOption, WizardOption } from './wizardConstants';

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
  classes: WizardClassOption[];
  species: WizardOption[];
  backgroundGroups: { label: string; options: { value: string; label: string }[] }[];
}

export default function WizardBasicsStep({ char, patch, classes, species, backgroundGroups }: Props) {
  return (
    <div className="space-y-5">
      <Field label="Name">
        <TextInput
          value={char.name}
          onChange={(e) => patch({ name: e.target.value })}
          placeholder="Character name"
        />
      </Field>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <Field label="Class">
          <ChoiceGroup
            value={char.class_name}
            onChange={(v) => patch({ class_name: v })}
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
