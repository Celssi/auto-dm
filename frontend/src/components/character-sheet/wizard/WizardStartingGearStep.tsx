import type { Character } from '../../../types';
import { Field } from '../../ui/forms/Field';

export interface StartingGearOption {
  id: string;
  label: string;
  description?: string;
}

interface Props {
  char: Character;
  classOptions: StartingGearOption[];
  backgroundOptions: StartingGearOption[];
  patch: (p: Partial<Character>) => void;
}

function GearSection({
  title,
  description,
  options,
  selected,
  onSelect,
}: {
  title: string;
  description?: string;
  options: StartingGearOption[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  if (options.length === 0) return null;
  return (
    <Field label={title}>
      {description && <p className="text-xs text-muted leading-relaxed mb-2">{description}</p>}
      <div className="space-y-2">
        {options.map((opt) => {
          const active = selected === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => onSelect(opt.id)}
              className={`w-full text-left rounded-lg border px-4 py-3 transition-colors ${
                active
                  ? 'border-accent/40 bg-accent/10 text-gray-100'
                  : 'border-border bg-bg/30 text-muted hover:border-accent/25 hover:text-gray-200'
              }`}
            >
              <span className="block font-medium text-sm">{opt.label}</span>
              {opt.description && (
                <span className="block text-xs mt-1 leading-relaxed opacity-90">{opt.description}</span>
              )}
            </button>
          );
        })}
      </div>
    </Field>
  );
}

export default function WizardStartingGearStep({ char, classOptions, backgroundOptions, patch }: Props) {
  if (!char.class_name) {
    return <p className="text-sm text-muted">Choose a class first.</p>;
  }

  const classSelected = char.starting_gear_choice || classOptions[0]?.id || '';
  const bgSelected = char.background_gear_choice || backgroundOptions[0]?.id || '';

  return (
    <div className="space-y-6">
      <GearSection
        title={classOptions.length > 1 ? 'Class starting equipment (pick 1)' : 'Class starting equipment'}
        description="PHB class kits only — gold-only class options are omitted."
        options={classOptions}
        selected={classSelected}
        onSelect={(id) => patch({ starting_gear_choice: id })}
      />
      {char.background && (
        <GearSection
          title="Background starting equipment (pick 1)"
          description="Each background offers a gear package (A) or 50 GP (B), in addition to class equipment."
          options={backgroundOptions}
          selected={bgSelected}
          onSelect={(id) => patch({ background_gear_choice: id })}
        />
      )}
      {classOptions.length === 0 && backgroundOptions.length === 0 && (
        <p className="text-sm text-muted">No starting equipment packages available.</p>
      )}
    </div>
  );
}
