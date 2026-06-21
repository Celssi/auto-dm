import type { Character } from '../../../types';
import { Field } from '../../ui/forms/Field';
import NumberInput from '../../ui/forms/NumberInput';
import { WIZARD_ABILITIES } from './wizardConstants';

function wizardBaseScore(char: Character, ability: (typeof WIZARD_ABILITIES)[number]): number {
  const base = char.base_ability_scores as Record<string, number> | undefined;
  if (base?.[ability] != null) return base[ability];
  return char.ability_scores[ability] ?? 10;
}

interface Props {
  char: Character;
  patch: (p: Partial<Character>) => void;
  onApplyStandardArray: () => void;
}

export default function WizardAbilitiesStep({ char, patch, onApplyStandardArray }: Props) {
  return (
    <div className="space-y-4">
      <button type="button" className="btn-ghost text-xs" onClick={onApplyStandardArray} disabled={!char.class_name}>
        Apply PHB standard array for class
      </button>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        {WIZARD_ABILITIES.map((ab) => (
          <Field key={ab} label={ab.toUpperCase()}>
            <NumberInput
              min={1}
              max={30}
              value={wizardBaseScore(char, ab)}
              onChange={(e) => {
                const n = parseInt(e.target.value) || 10;
                const baseScores = (char.base_ability_scores as Record<string, number> | undefined) ?? {};
                patch({
                  base_ability_scores: { ...baseScores, [ab]: n },
                  ability_scores_set: true,
                });
              }}
            />
          </Field>
        ))}
      </div>
    </div>
  );
}
