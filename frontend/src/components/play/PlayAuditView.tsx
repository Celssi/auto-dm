import { useMemo } from 'react';
import type { AuditEvent } from '../../api/client';
import { formatAuditSummary, formatAuditTime, isInferredAudit } from '../../pages/play/auditSummary';

export default function PlayAuditView({ auditEvents }: { auditEvents: AuditEvent[] }) {
  const visibleAudit = useMemo(() => auditEvents.slice(-30).reverse(), [auditEvents]);

  if (visibleAudit.length === 0) {
    return <p className="text-xs text-muted italic">Mechanical audit events will appear here.</p>;
  }

  return (
    <div className="space-y-1.5">
      {visibleAudit.map((event, idx) => (
        <div
          key={`audit-${event.ts ?? idx}-${event.event}-${idx}`}
          className="text-xs leading-relaxed text-gray-400 border-b border-border/40 pb-1.5 last:border-0 last:pb-0"
        >
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-muted tabular-nums">{formatAuditTime(event.ts)}</span>
            <span className="text-[10px] uppercase tracking-wide text-amber-200/80">
              {event.event.replace(/_/g, ' ')}
            </span>
            <span
              className={`text-[10px] px-1 py-0 rounded ${isInferredAudit(event) ? 'bg-purple-500/20 text-purple-200' : 'bg-emerald-500/15 text-emerald-200'}`}
            >
              {isInferredAudit(event) ? 'inferred' : 'code'}
            </span>
            {event.source && <span className="text-[10px] text-muted truncate">{event.source}</span>}
          </div>
          <p className="mt-0.5 text-gray-300">{formatAuditSummary(event)}</p>
        </div>
      ))}
    </div>
  );
}
