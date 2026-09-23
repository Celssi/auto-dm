import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { Shortcut } from '../../api/client';

const GROUPS: { title: string; ids: string[] }[] = [
  {
    title: 'Daily',
    ids: ['journey_day', 'aldwund_day', 'adventure_scene', 'resources'],
  },
  {
    title: 'Combat & recovery',
    ids: ['combat_setup', 'overcome_odds', 'recovery_health', 'recovery_morale', 'recovery_supplies'],
  },
  {
    title: 'Reference',
    ids: [
      'start_playing',
      'legacy_overview',
      'reason_ending',
      'adventure_overview',
      'random_character',
      'random_legacy',
      'reason',
      'background',
      'trinket',
    ],
  },
];

interface Props {
  shortcuts: Shortcut[];
  loading: string | null;
  onRun: (id: string) => void;
  embedded?: boolean;
}

function CollapsibleGroup({
  title,
  items,
  loading,
  onRun,
  defaultOpen,
}: {
  title: string;
  items: Shortcut[];
  loading: string | null;
  onRun: (id: string) => void;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen ?? true);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-muted hover:bg-panel-hover transition-colors"
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        {title}
        <span className="ml-auto text-[10px] opacity-60">{items.length}</span>
      </button>
      {open && (
        <div className="grid grid-cols-2 gap-1.5 p-2 pt-0">
          {items.map((s) => (
            <button
              key={s.id}
              type="button"
              className="play-chip text-left text-xs px-2 py-1.5 truncate"
              disabled={loading === s.id}
              onClick={() => onRun(s.id)}
            >
              {loading === s.id ? '…' : s.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ShortcutGroups({ shortcuts, loading, onRun, embedded }: Props) {
  const byId = Object.fromEntries(shortcuts.map((s) => [s.id, s]));

  const groups = GROUPS.flatMap((g) => {
    const items = g.ids.flatMap((id) => {
      const shortcut = byId[id];
      return shortcut ? [shortcut] : [];
    });
    return items.length > 0 ? [{ ...g, items }] : [];
  });

  const content = (
    <>
      {!embedded && <h2 className="section-heading mb-3">Shortcuts</h2>}
      <div className="space-y-2">
        {groups.map((g, i) => (
          <CollapsibleGroup
            key={g.title}
            title={g.title}
            items={g.items}
            loading={loading}
            onRun={onRun}
            defaultOpen={i === 0}
          />
        ))}
      </div>
    </>
  );

  if (embedded) return <div>{content}</div>;
  return <div className="panel-glow p-3">{content}</div>;
}
