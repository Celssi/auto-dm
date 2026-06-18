import { m } from '../../lib/framer';
import MarkdownContent from '../../components/ui/MarkdownContent';
import type { AdventureFull } from '../../api/client';

export default function AdventureDetailPanel({
  adventure,
  campaignName,
  onDelete,
}: {
  adventure: AdventureFull;
  campaignName?: string;
  onDelete?: () => void;
}) {
  const progress = adventure.player_progress;
  const completed = progress?.completed_beats ?? [];

  return (
    <m.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      className="panel-glow p-5 space-y-4 overflow-y-auto max-h-[75vh]"
    >
      {campaignName ? (
        <>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="label-text">Campaign</p>
              <h2 className="font-display text-xl text-gray-100">{campaignName}</h2>
            </div>
            {onDelete && (
              <button type="button" className="btn-danger text-sm" onClick={onDelete}>
                Delete adventure
              </button>
            )}
          </div>
        </>
      ) : (
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 className="font-display text-xl text-gray-100">{adventure.name}</h2>
          {onDelete && (
            <button type="button" className="btn-danger text-sm" onClick={onDelete}>
              Delete adventure
            </button>
          )}
        </div>
      )}

      <div className="rounded-lg border border-border bg-bg/40 p-4 space-y-3">
        <p className="label-text">Your story so far</p>
        {progress?.adventure_complete ? (
          <p className="text-sm text-accent">This adventure is complete.</p>
        ) : progress?.stage ? (
          <p className="text-sm text-muted">{progress.stage}</p>
        ) : (
          <p className="text-sm text-muted">Play to discover what happens next.</p>
        )}
        {completed.length > 0 ? (
          <ul className="text-sm text-gray-300 space-y-1 list-disc list-inside">
            {completed.map((beat) => (
              <li key={beat}>{beat}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted italic">No story beats completed yet.</p>
        )}
        <p className="text-xs text-muted leading-relaxed">
          The full adventure is hidden until you play through it. The DM guides the story based on your choices.
        </p>
      </div>

      {adventure.log && (
        <>
          <h3 className="section-heading pt-2">Adventure log</h3>
          <div className="rounded-lg border border-border bg-bg/40 p-4">
            <MarkdownContent content={adventure.log} className="text-xs" />
          </div>
        </>
      )}
    </m.div>
  );
}
