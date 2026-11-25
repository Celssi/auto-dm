import { useState } from 'react';
import { Dices, Layers, RotateCcw } from 'lucide-react';
import { api } from '../../api/client';

interface Props {
  characterId: string;
  remaining: number;
  onAction: (formatted: string) => void;
  embedded?: boolean;
}

/** Roll an expression like "d6", "2d6+1" or "d20-2". Returns null when it can't be parsed. */
export function rollDiceExpression(expr: string, random: () => number = Math.random): string | null {
  const m = expr
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '')
    .match(/^(\d*)d(\d+)([+-]\d+)?$/);
  if (!m) return null;
  const count = Math.min(Number(m[1] || 1), 50);
  const sides = Number(m[2]);
  if (count < 1 || sides < 2) return null;
  const mod = Number(m[3] || 0);
  const rolls = Array.from({ length: count }, () => 1 + Math.floor(random() * sides));
  const total = rolls.reduce((a, b) => a + b, 0) + mod;
  const modText = mod ? ` ${mod > 0 ? '+' : '-'} ${Math.abs(mod)}` : '';
  return `${expr.trim()}: [${rolls.join(', ')}]${modText} = ${total}`;
}

export default function DeckPanel({ characterId, remaining, onAction, embedded }: Props) {
  const [rollExpr, setRollExpr] = useState('d6');
  const [result, setResult] = useState('');

  const content = (
    <>
      <div className="flex items-center justify-between mb-3">
        <div className="section-heading mb-3">Table deck</div>
        <span className="text-[10px] text-muted border border-border rounded px-2 py-0.5 inline-flex items-center gap-1">
          <Layers className="w-3 h-3" />
          {remaining} left
        </span>
      </div>

      <div className="flex gap-2 mb-3">
        <button
          type="button"
          className="btn-primary flex-1"
          onClick={async () => {
            try {
              const res = await api.brambletrekDeckDraw(characterId, 1);
              const text = res.summary || res.cards?.join(', ') || 'Drew 1 card';
              setResult(text);
              onAction(text);
            } catch (e) {
              setResult(e instanceof Error ? e.message : 'Draw failed');
            }
          }}
        >
          Draw 1
        </button>
        <button
          type="button"
          className="btn-ghost flex-1 flex items-center justify-center gap-1"
          onClick={async () => {
            try {
              await api.brambletrekDeckReset(characterId);
              setResult('Deck reset');
              onAction('Deck reset');
            } catch (e) {
              setResult(e instanceof Error ? e.message : 'Reset failed');
            }
          }}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset
        </button>
      </div>

      <div className="flex gap-2">
        <input
          className="input flex-1 font-mono text-xs"
          value={rollExpr}
          onChange={(e) => setRollExpr(e.target.value)}
          placeholder="d6, 2d6+1…"
          aria-label="Dice roll expression"
        />
        <button
          type="button"
          className="btn-ghost flex items-center gap-1"
          onClick={() => setResult(rollDiceExpression(rollExpr) ?? `Can't roll "${rollExpr}" (try d6 or 2d6+1)`)}
        >
          <Dices className="w-3.5 h-3.5" />
          Roll
        </button>
      </div>
      {result && (
        <p className="mt-3 text-xs font-mono text-gray-200" role="status" aria-live="polite">
          {result}
        </p>
      )}
    </>
  );

  if (embedded) return <div>{content}</div>;
  return <div className="panel-glow p-3">{content}</div>;
}
