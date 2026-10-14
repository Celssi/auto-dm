import { useState } from 'react';
import { ChevronDown, MapPin, Users } from 'lucide-react';
import type { WorldEntry } from '../../api/client';
import MarkdownContent from '../ui/MarkdownContent';

interface Props {
  npcs: WorldEntry[];
  locations: WorldEntry[];
}

export default function WorldRosterPanel({ npcs, locations }: Props) {
  const [open, setOpen] = useState(true);
  const count = npcs.length + locations.length;

  return (
    <section className="rounded-lg border border-border bg-bg/40 shrink-0">
      <button
        type="button"
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="section-heading">NPCs & locations</span>
        <span className="inline-flex items-center gap-1 text-[10px] text-muted">
          {count}
          <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-3">
          <RosterGroup kind="npc" title="NPCs" icon={Users} entries={npcs} empty="No NPCs recorded yet." />
          <RosterGroup
            kind="location"
            title="Locations"
            icon={MapPin}
            entries={locations}
            empty="No locations recorded yet."
          />
        </div>
      )}
    </section>
  );
}

function RosterGroup({
  kind,
  title,
  icon: Icon,
  entries,
  empty,
}: {
  kind: 'npc' | 'location';
  title: string;
  icon: typeof Users;
  entries: WorldEntry[];
  empty: string;
}) {
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] uppercase tracking-wider text-muted inline-flex items-center gap-1.5">
        <Icon size={12} />
        {title}
      </p>
      {entries.length === 0 ? (
        <p className="text-xs text-muted italic">{empty}</p>
      ) : (
        <ul className="space-y-1">
          {entries.map((entry) => (
            <RosterItem key={`${kind}-${entry.name}`} entry={entry} />
          ))}
        </ul>
      )}
    </div>
  );
}

function RosterItem({ entry }: { entry: WorldEntry }) {
  const [open, setOpen] = useState(false);
  const body = entry.body.trim();
  return (
    <li className="rounded-md border border-border/80 bg-panel/40">
      <button
        type="button"
        className="w-full flex items-start justify-between gap-2 px-2.5 py-2 text-left"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="text-sm text-gray-100">{entry.name}</span>
        <ChevronDown size={14} className={`mt-0.5 text-muted shrink-0 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-2.5 pb-2">
          {body ? (
            <MarkdownContent content={body} className="text-xs" />
          ) : (
            <p className="text-xs text-muted italic">No notes yet.</p>
          )}
        </div>
      )}
    </li>
  );
}
