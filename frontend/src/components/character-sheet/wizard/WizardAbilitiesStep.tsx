import type { Character } from '../../../types';
import { Field } from '../../ui/forms/Field';
import NumberInput from '../../ui/forms/NumberInput';
import { WIZARD_ABILITIES } from './wizardConstants';

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
              value={char.ability_scores[ab] ?? 10}
              onChange={(e) => {
                const n = parseInt(e.target.value) || 10;
                const baseScores = (char.base_ability_scores as Record<string, number> | undefined) ?? {};
                patch({
                  ability_scores: { ...char.ability_scores, [ab]: n },
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
