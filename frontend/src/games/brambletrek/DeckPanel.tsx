import { useState } from 'react';
import { Dices, Layers, RotateCcw } from 'lucide-react';
import { api } from '../../api/client';

interface Props {
  characterId: string;
  remaining: number;
  onAction: (formatted: string) => void;
  embedded?: boolean;
}

export default function DeckPanel({ characterId, remaining, onAction, embedded }: Props) {
  const [rollExpr, setRollExpr] = useState('d6');

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
            const res = await api.brambletrekDeckDraw(characterId, 1);
            onAction(res.summary || res.cards?.join(', ') || 'Drew 1 card');
          }}
        >
          Draw 1
        </button>
        <button
          type="button"
          className="btn-ghost flex-1 flex items-center justify-center gap-1"
          onClick={async () => {
            await api.brambletrekDeckReset(characterId);
            onAction('Deck reset');
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
          onClick={() => onAction(`Roll ${rollExpr} (use chat or oracle)`)}
        >
          <Dices className="w-3.5 h-3.5" />
          Roll
        </button>
      </div>
    </>
  );

  if (embedded) return <div>{content}</div>;
  return <div className="panel-glow p-3">{content}</div>;
}
