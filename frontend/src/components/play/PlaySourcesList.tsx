import type { Source } from '../../api/client';

export default function PlaySourcesList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="shrink-0">
      <h2 className="section-heading mb-2">Sources</h2>
      <ul className="text-xs text-muted space-y-1">
        {sources.slice(0, 4).map((s) => (
          <li key={`${s.source_label}-${s.page}`} className="truncate">
            {s.source_label} p.{s.page}
          </li>
        ))}
      </ul>
    </div>
  );
}
