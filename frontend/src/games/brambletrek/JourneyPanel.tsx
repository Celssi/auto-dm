import { useState } from 'react';
import { AlertCircle, Check, Circle, Loader2, Sparkles } from 'lucide-react';
import PlayingCard from './PlayingCard';
import type { JourneyEvent, PendingJourney } from '../../types';

interface ApplyResult {
  summary?: string;
  item_error?: string | null;
}

interface Props {
  journey: PendingJourney | null;
  onApply: (index: number) => Promise<ApplyResult>;
  onDrawItem: (index: number) => Promise<{ item_error?: string | null }>;
  onStartCombat?: (index: number) => Promise<void>;
  onFinish: () => Promise<void>;
  onDiscard: () => Promise<void>;
  embedded?: boolean;
}

function EventRow({
  ev,
  isLast,
  onApply,
  onDrawItem,
  onStartCombat,
}: {
  ev: JourneyEvent;
  isLast: boolean;
  onApply: (index: number) => Promise<ApplyResult>;
  onDrawItem: (index: number) => Promise<{ item_error?: string | null }>;
  onStartCombat?: (index: number) => Promise<void>;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultText, setResultText] = useState<string | null>(null);
  const active = !ev.applied && ev.can_apply;

  const run = async (action: () => Promise<void>) => {
    setLoading(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center pt-1">
        <div
          className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
            ev.applied
              ? 'bg-success/20 text-success'
              : active
                ? 'bg-accent/20 text-accent ring-2 ring-accent/40'
                : 'bg-bg/60 text-muted border border-border'
          }`}
        >
          {ev.applied ? <Check className="w-3 h-3" /> : <span className="text-[10px] font-bold">{ev.index + 1}</span>}
        </div>
        {!isLast && <div className="w-px flex-1 min-h-[0.75rem] bg-border mt-1" />}
      </div>

      <div
        className={`flex-1 min-w-0 mb-3 rounded-xl border p-3 transition-colors ${
          ev.applied
            ? 'border-success/30 bg-success/10'
            : active
              ? 'border-accent/40 bg-accent/10'
              : 'border-border bg-bg/40'
        }`}
      >
        <div className="flex gap-3">
          <PlayingCard card={ev.card} applied={ev.applied} active={active} />
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wide text-muted mb-0.5">{ev.zone}</div>
                {ev.label ? (
                  <h4 className="text-sm font-medium leading-snug">{ev.label}</h4>
                ) : (
                  <h4 className="text-sm font-medium">Event {ev.index + 1}</h4>
                )}
              </div>
              {ev.applied && (
                <span className="text-[10px] text-success bg-success/15 border border-success/30 rounded px-1.5 py-0.5 shrink-0 inline-flex items-center gap-0.5">
                  <Check className="w-3 h-3" /> Done
                </span>
              )}
            </div>

            {ev.preview && ev.preview !== '—' && (
              <div className="mt-2 inline-flex items-center px-2 py-0.5 rounded-md bg-bg/60 border border-border text-[11px] text-muted">
                {ev.preview}
              </div>
            )}

            {ev.item_card && (
              <div className="mt-2 text-xs text-accent flex items-center gap-1">
                <Sparkles className="w-3 h-3 shrink-0" />
                <span>{ev.item_label || ev.item_card}</span>
              </div>
            )}

            {ev.combat_preview && <div className="mt-2 text-xs text-red-300">Opponent: {ev.combat_preview}</div>}

            {resultText && ev.applied && <p className="mt-2 text-xs text-success leading-relaxed">{resultText}</p>}

            {error && (
              <p className="mt-2 text-xs text-red-300 flex items-start gap-1">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                {error}
              </p>
            )}

            {!ev.applied && ev.combat && onStartCombat && (
              <button
                type="button"
                className="btn-ghost w-full mt-2 text-xs inline-flex items-center justify-center gap-1.5 border border-red-500/40 text-red-200"
                disabled={loading}
                onClick={() => run(() => onStartCombat(ev.index))}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Preparing…
                  </>
                ) : (
                  'Start combat'
                )}
              </button>
            )}

            {!ev.applied && (
              <button
                type="button"
                className="btn-primary w-full mt-3 text-xs inline-flex items-center justify-center gap-1.5"
                disabled={!ev.can_apply || loading}
                onClick={() =>
                  run(async () => {
                    const res = await onApply(ev.index);
                    if (res.summary) {
                      setResultText(res.summary.replace(/\*\*/g, ''));
                    }
                    if (res.item_error) {
                      setError(res.item_error);
                    }
                  })
                }
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Applying…
                  </>
                ) : active ? (
                  'Apply to sheet'
                ) : (
                  'Apply previous first'
                )}
              </button>
            )}
            {ev.applied && ev.needs_item && !ev.item_card && (
              <button
                type="button"
                className="btn-ghost w-full mt-3 text-xs inline-flex items-center justify-center gap-1.5"
                disabled={loading}
                onClick={() =>
                  run(async () => {
                    const res = await onDrawItem(ev.index);
                    if (res.item_error) setError(res.item_error);
                  })
                }
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Drawing…
                  </>
                ) : (
                  'Draw item'
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function JourneyPanel({
  journey,
  onApply,
  onDrawItem,
  onStartCombat,
  onFinish,
  onDiscard,
  embedded,
}: Props) {
  const [footerLoading, setFooterLoading] = useState<'finish' | 'discard' | null>(null);
  const [footerError, setFooterError] = useState<string | null>(null);

  if (!journey?.events?.length) {
    return (
      <div
        className={embedded ? 'text-sm text-muted py-8 text-center' : 'panel-glow p-6 text-sm text-muted text-center'}
      >
        <Circle className="w-8 h-8 mx-auto mb-2 opacity-30" />
        No journey draws yet. Use the Shortcuts tab or ask for a journey day.
      </div>
    );
  }

  const appliedCount = journey.events.filter((e) => e.applied).length;
  const total = journey.events.length;
  const progress = total > 0 ? (appliedCount / total) * 100 : 0;

  const runFooter = async (kind: 'finish' | 'discard', action: () => Promise<void>) => {
    setFooterLoading(kind);
    setFooterError(null);
    try {
      await action();
    } catch (e) {
      setFooterError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setFooterLoading(null);
    }
  };

  const content = (
    <div className="flex flex-col min-h-0">
      <div className="mb-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="section-heading">Today&apos;s draws</div>
          <span className="text-xs font-medium tabular-nums text-accent">
            {appliedCount}/{total} resolved
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-bg overflow-hidden border border-border">
          <div className="h-full bg-accent transition-all" style={{ width: `${progress}%` }} />
        </div>
        <p className="text-[11px] text-muted mt-2 leading-relaxed">
          Resolve in order. Apply each card before the next — pause for combat between events.
        </p>
      </div>

      <div className="space-y-0">
        {journey.events.map((ev, i) => (
          <EventRow
            key={ev.index}
            ev={ev}
            isLast={i === journey.events.length - 1}
            onApply={onApply}
            onDrawItem={onDrawItem}
            onStartCombat={onStartCombat}
          />
        ))}
      </div>

      {footerError && (
        <p className="mt-2 text-xs text-red-300 flex items-start gap-1">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          {footerError}
        </p>
      )}

      <div className="flex gap-2 mt-2 pt-3 border-t border-border sticky bottom-0 bg-panel/95 backdrop-blur-sm">
        <button
          type="button"
          className="btn-primary flex-1 inline-flex items-center justify-center gap-1.5"
          disabled={footerLoading !== null}
          onClick={() => runFooter('finish', onFinish)}
        >
          {footerLoading === 'finish' ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Finishing…
            </>
          ) : (
            'Finish day'
          )}
        </button>
        <button
          type="button"
          className="btn-ghost flex-1 border border-border rounded-lg py-2 inline-flex items-center justify-center gap-1.5"
          disabled={footerLoading !== null}
          onClick={() => runFooter('discard', onDiscard)}
        >
          {footerLoading === 'discard' ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Discarding…
            </>
          ) : (
            'Discard'
          )}
        </button>
      </div>
    </div>
  );

  if (embedded) return content;
  return <div className="panel-glow p-3">{content}</div>;
}
