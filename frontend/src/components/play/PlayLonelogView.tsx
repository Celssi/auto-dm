import { useMemo } from 'react';
import { visibleLonelogLines } from './lonelogUtils';

export default function PlayLonelogView({ lonelog }: { lonelog: string[] }) {
  const visibleLog = useMemo(() => visibleLonelogLines(lonelog), [lonelog]);

  if (visibleLog.length === 0) {
    return <p className="text-xs text-muted italic">Session events will appear here.</p>;
  }

  return (
    <div className="space-y-2">
      {visibleLog.map((line) => (
        <p
          key={`log-${line.slice(0, 40)}-${line.length}`}
          className="text-xs leading-relaxed text-gray-400 border-b border-border/40 pb-2 last:border-0 last:pb-0 whitespace-pre-wrap"
        >
          {line}
        </p>
      ))}
    </div>
  );
}
