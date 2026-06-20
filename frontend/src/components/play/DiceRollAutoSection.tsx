import { m } from '../../lib/framer';
import type { Advantage } from '../../pages/play/playState';
import DiceFace from './DiceFace';

interface Props {
  diceCount: number;
  advantage: Advantage;
  hasModifier: boolean;
  modifier: number;
  autoResult: number[] | null;
  rolling: boolean;
  onAutoRoll: () => void;
}

export default function DiceRollAutoSection({
  diceCount,
  advantage,
  hasModifier,
  modifier,
  autoResult,
  rolling,
  onAutoRoll,
}: Props) {
  const modSign = modifier >= 0 ? '+' : '';
  const autoChosen =
    autoResult && autoResult.length === 2
      ? advantage === 'advantage'
        ? Math.max(...autoResult)
        : Math.min(...autoResult)
      : (autoResult?.[0] ?? null);
  const autoTotal = autoChosen != null && hasModifier ? autoChosen + modifier : autoChosen;

  return (
    <div className="space-y-3">
      <div className="flex justify-center gap-4 py-2">
        {Array.from({ length: diceCount }, (_, i) => {
          const isChosen =
            autoResult && diceCount === 2
              ? autoResult[i] === (advantage === 'advantage' ? Math.max(...autoResult) : Math.min(...autoResult))
              : true;
          return (
            <DiceFace
              key={i}
              value={autoResult?.[i] ?? null}
              rolling={rolling}
              chosen={autoResult != null && isChosen}
              dimmed={autoResult != null && !isChosen}
            />
          );
        })}
      </div>

      {autoResult && !rolling && (
        <m.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center text-sm text-gray-300"
        >
          {diceCount === 2 && (
            <span className="text-muted">
              {advantage === 'advantage' ? 'Keep highest: ' : 'Keep lowest: '}
              <span className="text-gray-200 font-semibold">{autoChosen}</span>
              {' · '}
            </span>
          )}
          {hasModifier ? (
            <span>
              {autoChosen} {modSign}
              {modifier} = <span className="text-accent font-display text-lg font-semibold">{autoTotal}</span>
            </span>
          ) : (
            <span>
              Result: <span className="text-accent font-display text-lg font-semibold">{autoChosen}</span>
            </span>
          )}
        </m.div>
      )}

      {!autoResult && !rolling && (
        <div className="flex justify-center">
          <button type="button" className="btn-primary px-8 py-2 font-display text-base" onClick={onAutoRoll}>
            Roll!
          </button>
        </div>
      )}
    </div>
  );
}
