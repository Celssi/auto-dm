import { m } from '../../lib/framer';
import type { Advantage } from '../../pages/play/playState';

export default function DiceResultLine({
  diceCount,
  advantage,
  chosen,
  hasModifier,
  modifier,
}: {
  diceCount: number;
  advantage: Advantage;
  chosen: number | null;
  hasModifier: boolean;
  modifier: number;
}) {
  const modSign = modifier >= 0 ? '+' : '';
  const total = chosen != null && hasModifier ? chosen + modifier : chosen;

  return (
    <m.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="text-center text-sm text-gray-300">
      {diceCount === 2 && (
        <span className="text-muted">
          {advantage === 'advantage' ? 'Keep highest: ' : 'Keep lowest: '}
          <span className="text-gray-200 font-semibold">{chosen}</span>
          {' · '}
        </span>
      )}
      {hasModifier ? (
        <span>
          {chosen} {modSign}
          {modifier} = <span className="text-accent font-display text-lg font-semibold">{total}</span>
        </span>
      ) : (
        <span>
          Result: <span className="text-accent font-display text-lg font-semibold">{chosen}</span>
        </span>
      )}
    </m.div>
  );
}
