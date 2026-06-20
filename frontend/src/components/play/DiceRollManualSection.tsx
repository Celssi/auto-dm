import { m } from '../../lib/framer';
import type { Advantage } from '../../pages/play/playState';
import DiceFace from './DiceFace';

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
  const modSign = modifier >= 0 ? '+' : '';
  const chosenManual =
    diceCount === 2 && manualValues.every((v) => v != null)
      ? advantage === 'advantage'
        ? Math.max(...(manualValues as number[]))
        : Math.min(...(manualValues as number[]))
      : manualValues[0];
  const manualTotal = chosenManual != null && hasModifier ? chosenManual + modifier : chosenManual;

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

      {canSubmitManual && (
        <m.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center text-sm text-gray-300"
        >
          {diceCount === 2 && (
            <span className="text-muted">
              {advantage === 'advantage' ? 'Keep highest: ' : 'Keep lowest: '}
              <span className="text-gray-200 font-semibold">{chosenManual}</span>
              {' · '}
            </span>
          )}
          {hasModifier ? (
            <span>
              {chosenManual} {modSign}
              {modifier} = <span className="text-accent font-display text-lg font-semibold">{manualTotal}</span>
            </span>
          ) : (
            <span>
              Result: <span className="text-accent font-display text-lg font-semibold">{chosenManual}</span>
            </span>
          )}
        </m.div>
      )}
    </div>
  );
}
