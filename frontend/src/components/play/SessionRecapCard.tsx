import { useState } from 'react';
import { ChevronDown, Clapperboard } from 'lucide-react';
import MarkdownContent from '../ui/MarkdownContent';

interface Props {
  text: string;
  loading?: boolean;
}

export default function SessionRecapCard({ text, loading = false }: Props) {
  const [open, setOpen] = useState(true);
  if (!loading && !text.trim()) return null;

  return (
    <section className="rounded-xl border border-accent/25 bg-accent/5 overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="inline-flex items-center gap-2 font-display text-sm text-accent">
          <Clapperboard size={16} />
          Previously on…
        </span>
        <ChevronDown size={16} className={`text-muted transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-4 pb-4">
          {loading && !text.trim() ? (
            <p className="text-sm text-muted animate-pulse">Gathering the story so far…</p>
          ) : (
            <MarkdownContent content={text} className="text-sm leading-relaxed" />
          )}
        </div>
      )}
    </section>
  );
}
