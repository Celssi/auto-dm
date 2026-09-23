import { useState } from 'react';
import { AlertCircle, Heart, Loader2, Shield, Swords } from 'lucide-react';
import PlayingCard from './PlayingCard';
import type { BrambletrekCombatState } from '../../types';

interface Props {
  combat: BrambletrekCombatState;
  onAction: (action: string, handIndex?: number) => Promise<void>;
  embedded?: boolean;
}

function HpBar({ current, max, label, accent }: { current: number; max: number; label: string; accent: string }) {
  const pct = max > 0 ? Math.round((current / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-muted">{label}</span>
        <span className="tabular-nums">
          {current}/{max}
        </span>
      </div>
      <div className="h-2 rounded-full bg-bg border border-border overflow-hidden">
        <div className={`h-full transition-all ${accent}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function BrambletrekCombatPanel({ combat, onAction, embedded }: Props) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (action: string, handIndex?: number) => {
    setLoading(action);
    setError(null);
    try {
      await onAction(action, handIndex);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Combat action failed');
    } finally {
      setLoading(null);
    }
  };

  const playerHp = combat.player?.hp ?? 0;
  const opp = combat.opponent ?? { label: 'Opponent', hp: 0, max_hp: 0 };
  const turn = combat.turn ?? 'opponent';
  const isActive = combat.status === 'active';
  const isFinale = combat.mode === 'aerith_finale';

  const content = (
    <div className="flex flex-col gap-3 min-h-0">
      <div className="flex items-center justify-between gap-2">
        <div className="section-heading flex items-center gap-1.5">
          <Swords className="w-3.5 h-3.5" />
          Combat
        </div>
        <span className="text-[10px] uppercase tracking-wide text-accent">
          {combat.status === 'active' ? `Turn: ${turn}` : combat.status}
        </span>
      </div>

      {isFinale && combat.finale_phase && (
        <div className="text-xs text-accent space-y-1">
          <div>Aerith phase {combat.finale_phase}</div>
          {combat.phase_goals && combat.phase_progress && (
            <div className="text-[10px] text-muted">
              Damage {String((combat.phase_progress as { damage_dealt?: number }).damage_dealt ?? 0)}/
              {combat.phase_goals.damage_goal ?? 20}
              {' · '}
              Rounds {String((combat.phase_progress as { rounds?: number }).rounds ?? 0)}/
              {combat.phase_goals.rounds_goal ?? 4}
            </div>
          )}
          {combat.buffs?.critical && (
            <div className="text-[10px] text-amber-300">Critical Chance active</div>
          )}
        </div>
      )}

      <HpBar current={playerHp} max={20} label="Your health" accent="bg-success" />
      <HpBar
        current={opp.hp ?? 0}
        max={opp.max_hp ?? opp.hp ?? 10}
        label={opp.label || 'Opponent'}
        accent="bg-red-500"
      />

      {combat.initiative && (
        <div className="text-[11px] text-muted flex gap-3">
          <span>You: {combat.initiative.player_card}</span>
          <span>Opp: {combat.initiative.opponent_card}</span>
        </div>
      )}

      {isActive && turn === 'player' && (combat.tactic_hand?.length ?? 0) > 0 && (
        <div>
          <div className="text-[11px] text-muted mb-2 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            Tactic hand — play one card
          </div>
          <div className="grid grid-cols-2 gap-2">
            {(combat.tactic_hand ?? []).map((card, i) => (
              <button
                key={`${card}-${i}`}
                type="button"
                className="rounded-lg border border-border bg-bg/60 p-2 hover:border-accent/50 transition-colors"
                disabled={loading !== null}
                onClick={() => run('play_tactic', i)}
              >
                <PlayingCard card={card} size="sm" />
              </button>
            ))}
          </div>
        </div>
      )}

      {isActive && turn === 'player' && combat.can_search_item && !combat.item_used_this_phase && (
        <button
          type="button"
          className="btn-ghost w-full text-xs border border-accent/30"
          disabled={loading !== null}
          onClick={() => run('search_item')}
        >
          {loading === 'search_item' ? 'Searching…' : 'Search for item (once per phase)'}
        </button>
      )}

      {(combat.combat_items?.length ?? 0) > 0 && (
        <div className="text-[11px] text-muted">
          Items found: {combat.combat_items?.join(', ')}
        </div>
      )}

      {isActive && combat.can_advance_phase && (
        <button
          type="button"
          className="btn-primary w-full text-xs"
          disabled={loading !== null}
          onClick={() => run('advance_phase')}
        >
          {loading === 'advance_phase' ? 'Advancing…' : 'Advance to next phase'}
        </button>
      )}

      {isActive && (
        <div className="flex flex-col gap-2">
          {turn === 'opponent' && (
            <button
              type="button"
              className="btn-primary w-full text-xs"
              disabled={loading !== null}
              onClick={() => run('opponent_turn')}
            >
              {loading === 'opponent_turn' ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin inline mr-1" />
                  Opponent acts…
                </>
              ) : (
                'Resolve opponent turn'
              )}
            </button>
          )}
          {isFinale && turn === 'eolan' && (
            <button
              type="button"
              className="btn-ghost w-full text-xs border border-accent/40"
              disabled={loading !== null}
              onClick={() => run('eolan_turn')}
            >
              {loading === 'eolan_turn' ? 'Eolan acts…' : "Resolve Eolan's turn"}
            </button>
          )}
        </div>
      )}

      {combat.status === 'won' && (
        <div className="rounded-lg border border-success/40 bg-success/10 px-3 py-2 text-xs text-success flex items-center gap-1.5">
          <Heart className="w-3.5 h-3.5" />
          Victory! Apply the journey event when ready.
        </div>
      )}
      {combat.status === 'lost' && (
        <div className="rounded-lg border border-red-500/40 bg-red-900/20 px-3 py-2 text-xs text-red-200">
          Defeated — your Gnawborn will reawaken in the deep forest.
        </div>
      )}

      {(combat.log?.length ?? 0) > 0 && (
        <div className="text-[11px] text-muted space-y-1 max-h-32 overflow-y-auto border-t border-border pt-2">
          {(combat.log ?? []).map((line) => (
            <p key={line} className="leading-relaxed">
              {line.replace(/\*\*/g, '')}
            </p>
          ))}
        </div>
      )}

      {error && (
        <p className="text-xs text-red-300 flex items-start gap-1">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          {error}
        </p>
      )}
    </div>
  );

  if (embedded) return content;
  return <div className="panel-glow p-3">{content}</div>;
}
