import type { Advantage } from '../../pages/play/playState';
import DiceResultLine from './DiceResultLine';

interface Props {
  diceCount: number;
  advantage: Advantage;
  manualValues: (number | null)[];
  hasModifier: boolean;
  modifier: number;
  canSubmitManual: boolean;
  onManualValue: (index: number, raw: string) => void;
}

export default function DiceRollManualSection({
  diceCount,
  advantage,
  manualValues,
  hasModifier,
  modifier,
  canSubmitManual,
  onManualValue,
}: Props) {
  const chosenManual =
    diceCount === 2 && manualValues.every((v) => v != null)
      ? advantage === 'advantage'
        ? Math.max(...(manualValues as number[]))
        : Math.min(...(manualValues as number[]))
      : manualValues[0];

  return (
    <div className="space-y-3">
      <div className="flex justify-center gap-4">
        {Array.from({ length: diceCount }, (_, i) => (
          <div key={i} className="flex flex-col items-center gap-1">
            <input
              type="number"
              min={1}
              max={20}
              value={manualValues[i] ?? ''}
              onChange={(e) => onManualValue(i, e.target.value)}
              placeholder="d20"
              aria-label={diceCount === 2 ? `Die ${i + 1} roll` : 'd20 roll'}
              className="input tabular-nums w-20 text-center text-2xl font-display py-3"
            />
            {diceCount === 2 && <span className="text-[10px] text-muted">{i === 0 ? 'Die 1' : 'Die 2'}</span>}
          </div>
        ))}
      </div>

      {canSubmitManual && chosenManual != null && (
        <DiceResultLine
          diceCount={diceCount}
          advantage={advantage}
          chosen={chosenManual}
          hasModifier={hasModifier}
          modifier={modifier}
        />
      )}
    </div>
  );
}
