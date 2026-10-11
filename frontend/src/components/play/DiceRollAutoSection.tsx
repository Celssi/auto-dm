import type { Advantage } from '../../pages/play/playState';
import DiceFace from './DiceFace';
import DiceResultLine from './DiceResultLine';

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
  const autoChosen =
    autoResult && autoResult.length === 2
      ? advantage === 'advantage'
        ? Math.max(...autoResult)
        : Math.min(...autoResult)
      : (autoResult?.[0] ?? null);

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
        <DiceResultLine
          diceCount={diceCount}
          advantage={advantage}
          chosen={autoChosen}
          hasModifier={hasModifier}
          modifier={modifier}
        />
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
