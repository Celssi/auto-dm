import type { Source } from '../../api/client';
import { useBookReader } from '../../context/BookReaderContext';
import { matchBookBySource } from '../../lib/books';

export default function PlaySourcesList({ sources }: { sources: Source[] }) {
  const { books, openSource } = useBookReader();
  if (sources.length === 0) return null;

  return (
    <div className="shrink-0">
      <h2 className="section-heading mb-2">Sources</h2>
      <ul className="text-xs text-muted space-y-1">
        {sources.slice(0, 4).map((source) => {
          const canOpen = Boolean(matchBookBySource(books, source.source_label));
          const label = `${source.source_label} p.${source.page}`;
          return (
            <li key={`${source.source_label}-${source.page}`}>
              {canOpen ? (
                <button
                  type="button"
                  className="truncate text-left w-full text-accent hover:underline min-h-11"
                  onClick={() => openSource(source.source_label, source.page)}
                >
                  {label}
                </button>
              ) : (
                <span className="truncate block">{label}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
