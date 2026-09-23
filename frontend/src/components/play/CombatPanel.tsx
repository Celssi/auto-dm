import { useState } from 'react';
import type { CombatStateSnapshot } from '../../api/client';

type Props = {
  state: CombatStateSnapshot;
  onAction?: (action: string, targetId?: string) => void;
};

export default function CombatPanel({ state, onAction }: Props) {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const byId = new Map(state.combatants.map((c) => [c.id, c]));
  const player = state.combatants.find((c) => c.kind === 'player');
  const isPlayerTurn = state.current_combatant_id === 'player';
  const livingEnemies = state.combatants.filter((c) => c.kind === 'enemy' && c.hp > 0);
  const targetId = selectedTarget ?? (livingEnemies.length === 1 ? livingEnemies[0].id : null);

  return (
    <div className="shrink-0 rounded-lg border border-red-500/30 bg-red-500/5 p-2.5 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-red-300/90">Combat</h2>
        <span className="text-[10px] text-muted">Round {state.round}</span>
      </div>
      <p className="text-sm font-medium text-gray-200 truncate" title={state.encounter_name}>
        {state.encounter_name}
      </p>
      {player && (
        <p className="text-[11px] text-muted">
          You: HP {player.hp}/{player.max_hp} · AC {player.ac}
          {player.attack_bonus != null && player.damage ? (
            <span>
              {' '}
              · Attack +{player.attack_bonus} ({player.damage})
            </span>
          ) : null}
        </p>
      )}
      <ol className="space-y-1 max-h-[10rem] overflow-y-auto pr-0.5">
        {state.order.map((id) => {
          const c = byId.get(id);
          if (!c) return null;
          const isCurrent = id === state.current_combatant_id;
          const down = c.hp <= 0;
          const isEnemy = c.kind === 'enemy';
          const selectable = isPlayerTurn && isEnemy && !down && onAction;
          return (
            <li key={id}>
              <button
                type="button"
                disabled={!selectable}
                onClick={() => selectable && setSelectedTarget(id)}
                className={`w-full text-left text-xs rounded px-2 py-1 border ${
                  isCurrent ? 'border-accent/50 bg-accent/10 text-gray-100' : 'border-border/50 bg-bg/30 text-gray-400'
                } ${down ? 'opacity-50 line-through' : ''} ${
                  selectedTarget === id ? 'ring-1 ring-accent/60' : ''
                } ${selectable ? 'hover:border-accent/40 cursor-pointer' : ''}`}
              >
                <span className="font-medium">{c.name}</span>
                {isEnemy && (
                  <span className="text-muted ml-1">
                    HP {c.hp}/{c.max_hp} · AC {c.ac}
                  </span>
                )}
                {isCurrent && <span className="ml-1 text-accent text-[10px] uppercase">turn</span>}
              </button>
            </li>
          );
        })}
      </ol>
      {onAction && isPlayerTurn && (
        <div className="flex flex-wrap gap-2 pt-1">
          <button
            type="button"
            disabled={!targetId}
            onClick={() => targetId && onAction('attack', targetId)}
            className="text-xs px-2.5 py-1 rounded bg-red-600/80 hover:bg-red-600 disabled:opacity-40 text-white font-medium"
          >
            Attack
          </button>
          <button
            type="button"
            onClick={() => onAction('end_turn')}
            className="text-xs px-2.5 py-1 rounded border border-border/60 hover:bg-bg/50 text-gray-300"
          >
            End turn
          </button>
        </div>
      )}
    </div>
  );
}
