import { useState } from 'react';
import { m } from '../../lib/framer';
import type { Character, ClassLevel } from '../../types';
import { Field } from '../ui/forms/Field';
import TextInput from '../ui/forms/TextInput';
import NumberInput from '../ui/forms/NumberInput';
import ChoiceGroup from '../ui/forms/ChoiceGroup';
import SegmentedControl from '../ui/forms/SegmentedControl';
import NumberStepper from '../ui/forms/NumberStepper';
import { displayLabel } from '../../lib/displayText';

interface Summary {
  asi_feat_slots?: number;
  asi_feat_taken?: number;
  needs_asi?: boolean;
  hit_die?: number;
  classes?: ClassLevel[];
  multiclass?: boolean;
}

interface Props {
  character: Character;
  summary: Summary;
  onConfirm: (hpRoll: number | undefined, asiChoices: Record<string, unknown>[], className?: string) => void;
  onCancel: () => void;
}

const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const;

export default function LevelUpDialog({ character, summary, onConfirm, onCancel }: Props) {
  const classEntries = (
    summary.classes?.length ? summary.classes : [{ class_name: character.class_name, level: character.level }]
  ) as ClassLevel[];
  const [targetClass, setTargetClass] = useState(classEntries[0]?.class_name || character.class_name);
  const selected = classEntries.find((c) => c.class_name === targetClass) || classEntries[0];
  const hitDie = summary.hit_die || character.hit_die || 8;
  const [hpMode, setHpMode] = useState<'roll' | 'average'>('roll');
  const [hpRoll, setHpRoll] = useState<number | ''>('');
  const asiChoices = (character.asi_choices || []) as Record<string, unknown>[];
  const [localAsi, setLocalAsi] = useState<Record<string, unknown>[]>(asiChoices);
  const needsAsi = summary.needs_asi;

  const addAsi = () => setLocalAsi([...localAsi, { type: 'asi', plus: { str: 2 } }]);
  const addFeat = () => setLocalAsi([...localAsi, { type: 'feat', feat: '' }]);

  const confirm = () => {
    const roll = hpMode === 'average' ? Math.floor(hitDie / 2) + 1 : hpRoll === '' ? undefined : Number(hpRoll);
    onConfirm(roll, localAsi, targetClass);
  };

  const classOptions = classEntries.map((c) => ({
    value: c.class_name,
    label: `${displayLabel(c.class_name)} (Lv ${c.level})`,
  }));

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <m.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="panel-glow p-6 max-w-md w-full space-y-4 shadow-glow max-h-[90vh] overflow-y-auto"
      >
        <h2 className="font-display text-lg font-semibold text-accent">Level up → total {character.level + 1}</h2>

        {classEntries.length > 1 && (
          <Field label="Which class gains a level?">
            <ChoiceGroup value={targetClass} onChange={setTargetClass} options={classOptions} columns={2} />
          </Field>
        )}

        <Field label={`Hit Points (d${hitDie} + CON), ${displayLabel(selected?.class_name || character.class_name)}`}>
          <SegmentedControl
            value={hpMode}
            onChange={(v) => setHpMode(v as 'roll' | 'average')}
            options={[
              { value: 'roll', label: 'Roll' },
              { value: 'average', label: `Average (${Math.floor(hitDie / 2) + 1})` },
            ]}
          />
          {hpMode === 'roll' && (
            <NumberInput
              className="mt-2"
              min={1}
              max={hitDie}
              placeholder={`1-${hitDie}`}
              value={hpRoll}
              onChange={(e) => setHpRoll(e.target.value === '' ? '' : parseInt(e.target.value))}
            />
          )}
        </Field>

        {needsAsi && (
          <Field label={`ASI / Feat (${summary.asi_feat_taken}/${summary.asi_feat_slots} taken)`}>
            <div className="space-y-3 max-h-48 overflow-y-auto">
              {localAsi.map((choice, i) => (
                <div
                  key={`asi-${choice.type}-${i}-${choice.type === 'feat' ? String(choice.feat || '') : 'plus'}`}
                  className="text-xs border border-border rounded-lg p-3 bg-bg/30"
                >
                  {choice.type === 'feat' ? (
                    <TextInput
                      inputClassName="text-xs"
                      placeholder="Feat name"
                      value={String(choice.feat || '')}
                      onChange={(e) => {
                        const next = [...localAsi];
                        next[i] = { ...choice, feat: e.target.value };
                        setLocalAsi(next);
                      }}
                    />
                  ) : (
                    <div className="space-y-2">
                      <p className="text-muted">Assign +2 to one ability, or +1 to two:</p>
                      <div className="grid grid-cols-2 gap-2">
                        {ABILITIES.map((ab) => (
                          <NumberStepper
                            key={ab}
                            label={ab}
                            value={Number((choice.plus as Record<string, number>)?.[ab] || 0)}
                            min={0}
                            max={2}
                            onChange={(n) => {
                              const next = [...localAsi];
                              const plus = { ...(choice.plus as Record<string, number>) };
                              plus[ab] = n;
                              next[i] = { ...choice, plus };
                              setLocalAsi(next);
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-2">
              <button type="button" className="btn-ghost text-xs" onClick={addAsi}>
                + ASI
              </button>
              <button type="button" className="btn-ghost text-xs" onClick={addFeat}>
                + Feat
              </button>
            </div>
          </Field>
        )}

        <div className="flex gap-2 justify-end pt-2">
          <button type="button" className="btn-ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={confirm}>
            Level up
          </button>
        </div>
      </m.div>
    </div>
  );
}
