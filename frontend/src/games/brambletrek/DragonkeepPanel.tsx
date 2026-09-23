import { useState } from 'react';
import { AlertCircle, Castle, Loader2, MapPin, RotateCcw } from 'lucide-react';
import type { DragonkeepState } from '../../types';

const ACTION_LABELS: Record<string, string> = {
  advance_path: 'Continue along the path',
  draw_path: 'Draw card for this location',
  apply_path: 'Apply outcome to sheet',
  enter_gems: 'Enter the Room of Gems',
  choose_gem_tempest: 'Lift the Azure Gem (Tempest)',
  choose_gem_pyre: 'Lift the Crimson Gem (Pyre)',
  choose_gem_leaf: 'Lift the Verdant Gem (Leaf)',
  start_exploration: 'Draw 3 exploration cards',
  to_antechamber: 'Proceed to antechamber (Eolan)',
  to_door: 'Approach the Door of Lunar Light',
  open_door: 'Place the Oracle relic',
  advance_finale: 'Face Aerith with Eolan',
  advance_finale_phase: 'Advance to next Aerith phase',
  eolan_ally_draw: "Draw Eolan's tactic",
  reset: 'Reset Dragonkeep progress',
};

interface Props {
  state: DragonkeepState | null;
  onAction: (action: string) => Promise<void>;
  onInit: () => Promise<void>;
  embedded?: boolean;
}

export default function DragonkeepPanel({ state, onAction, onInit, embedded }: Props) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (action: string) => {
    setLoading(action);
    setError(null);
    try {
      await onAction(action);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setLoading(null);
    }
  };

  if (!state) {
    return (
      <div className={embedded ? 'text-sm text-muted py-6 text-center' : 'panel-glow p-6 text-center'}>
        <Castle className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm text-muted mb-3">
          Dragonkeep phase tracker — set active adventure to Dungeons of Dragonkeep.
        </p>
        <button type="button" className="btn-primary text-xs" onClick={() => onInit()}>
          Begin the path
        </button>
      </div>
    );
  }

  const pathProgress =
    state.phase === 'path'
      ? Math.round((state.path_step / state.path_total) * 100)
      : state.phase === 'finale'
        ? 100
        : 70;

  const content = (
    <div className="flex flex-col min-h-0 gap-3">
      <div>
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="section-heading flex items-center gap-1.5">
            <Castle className="w-3.5 h-3.5" />
            {state.module_label}
          </div>
          <span className="text-[10px] uppercase tracking-wide text-accent">{state.phase_label}</span>
        </div>
        <div className="h-1.5 rounded-full bg-bg overflow-hidden border border-border">
          <div className="h-full bg-accent transition-all" style={{ width: `${pathProgress}%` }} />
        </div>
      </div>

      {state.phase === 'path' && state.location_title && (
        <div className="rounded-xl border border-border bg-bg/40 p-3">
          <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
            <MapPin className="w-3.5 h-3.5" />
            Location {state.path_step} / {state.path_total} — {state.location_title}
          </div>
          {state.location_body && (
            <p className="text-xs text-muted leading-relaxed line-clamp-4">{state.location_body}</p>
          )}
        </div>
      )}

      {state.pending_path_card && (
        <div className="rounded-lg border border-accent/30 bg-accent/10 px-3 py-2 text-xs">
          <span className="font-medium">{state.pending_path_card}</span>
          {state.pending_path_label && <span className="text-muted"> — {state.pending_path_label}</span>}
          {state.pending_path_preview && state.pending_path_preview !== '—' && (
            <div className="text-muted mt-1">{state.pending_path_preview}</div>
          )}
        </div>
      )}

      {state.gems_completed.length > 0 && (
        <div className="text-[11px] text-muted">
          Completed paths: {state.gems_completed.map((g) => g.replace('path_of_', '')).join(', ')}
        </div>
      )}

      {state.combat_preview && (
        <div className="rounded-lg border border-red-500/30 bg-red-900/20 px-3 py-2 text-xs text-red-200">
          Active combat: {state.combat_preview}. Open the <strong>Combat</strong> tab.
        </div>
      )}

      {state.phase === 'finale' && state.finale_step_label && (
        <div className="text-[11px] text-accent">
          Finale: {state.finale_step_label}
          {state.finale_phase && state.finale_step === 'dragon' ? ` — phase ${state.finale_phase}` : ''}
        </div>
      )}

      <p className="text-xs leading-relaxed text-muted">{state.instructions}</p>

      {error && (
        <p className="text-xs text-red-300 flex items-start gap-1">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          {error}
        </p>
      )}

      <div className="flex flex-col gap-2">
        {state.actions.map((action) => (
          <button
            key={action}
            type="button"
            className="btn-primary w-full text-xs inline-flex items-center justify-center gap-1.5"
            disabled={loading !== null}
            onClick={() => run(action)}
          >
            {loading === action ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Working…
              </>
            ) : (
              ACTION_LABELS[action] || action
            )}
          </button>
        ))}
      </div>

      {state.phase === 'exploration' && (
        <p className="text-[11px] text-accent">
          Switch to the <strong>Journey</strong> tab to resolve your 3 cards, then Finish day.
        </p>
      )}

      <button
        type="button"
        className="btn-ghost text-[11px] inline-flex items-center justify-center gap-1 border border-border rounded-lg py-1.5"
        disabled={loading !== null}
        onClick={() => (state ? run('reset') : onInit())}
      >
        <RotateCcw className="w-3 h-3" />
        Reset progress
      </button>
    </div>
  );

  if (embedded) return content;
  return <div className="panel-glow p-3">{content}</div>;
}
