import type { Character } from '../../../../types';
import { Field } from '../../../../components/ui/forms/Field';
import NumberInput from '../../../../components/ui/forms/NumberInput';
import ChoiceGroup from '../../../../components/ui/forms/ChoiceGroup';
import SegmentedControl from '../../../../components/ui/forms/SegmentedControl';
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
  backgroundAbilities: string[];
}

export default function WizardAbilitiesStep({
  char,
  patch,
  onApplyStandardArray,
  backgroundAbilities,
}: Props) {
  const options = backgroundAbilities.map((ab) => ({
    value: ab,
    label: ab.toUpperCase(),
  }));
  const mode = char.background_asi_all_three ? 'spread' : 'plus';
  const plus2 = String(char.background_asi_plus2 || '');
  const plus1 = String(char.background_asi_plus1 || '');

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
      {options.length >= 2 && (
        <div className="space-y-3 rounded-lg border border-border p-4">
          <p className="text-sm text-muted leading-relaxed">
            Background ability increase: put +2 in one listed ability and +1 in another, or put +1 in all three.
          </p>
          <Field label="Increase pattern">
            <SegmentedControl
              value={mode}
              onChange={(next) => {
                if (next === 'spread') {
                  patch({
                    background_asi_all_three: true,
                    background_asi_plus2: '',
                    background_asi_plus1: '',
                    background_asi_mode: 'auto',
                  });
                  return;
                }
                patch({
                  background_asi_all_three: false,
                  background_asi_mode: 'auto',
                });
              }}
              options={[
                { value: 'plus', label: '+2 / +1' },
                { value: 'spread', label: '+1 / +1 / +1' },
              ]}
            />
          </Field>
          {mode === 'plus' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="+2 ability">
                <ChoiceGroup
                  value={plus2}
                  onChange={(v) =>
                    patch({
                      background_asi_plus2: v,
                      background_asi_plus1: plus1 === v ? '' : plus1,
                      background_asi_all_three: false,
                      background_asi_mode: 'auto',
                    })
                  }
                  options={options}
                  allowEmpty
                  columns={3}
                />
              </Field>
              <Field label="+1 ability">
                <ChoiceGroup
                  value={plus1}
                  onChange={(v) =>
                    patch({
                      background_asi_plus1: v,
                      background_asi_plus2: plus2 === v ? '' : plus2,
                      background_asi_all_three: false,
                      background_asi_mode: 'auto',
                    })
                  }
                  options={options.filter((opt) => opt.value !== plus2)}
                  allowEmpty
                  columns={3}
                />
              </Field>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
