import type { Shortcut } from '../../api/client';
import ShortcutGroups from '../../games/brambletrek/ShortcutGroups';

interface Props {
  shortcuts: Shortcut[];
  loading: boolean;
  onRun: (id: string) => void;
  grouped?: boolean;
  shortcutLoading?: string | null;
}

export default function PlayShortcutGrid({ shortcuts, loading, onRun, grouped, shortcutLoading }: Props) {
  if (grouped) {
    return (
      <div className="shrink-0">
        <ShortcutGroups shortcuts={shortcuts} loading={shortcutLoading ?? null} onRun={onRun} embedded />
      </div>
    );
  }

  return (
    <div className="shrink-0">
      <h2 className="section-heading mb-1.5">Shortcuts</h2>
      <div className="grid grid-cols-2 gap-1 max-h-[11rem] overflow-y-auto pr-0.5">
        {shortcuts.map((s) => (
          <button
            key={s.id}
            type="button"
            className="play-chip text-left"
            onClick={() => onRun(s.id)}
            disabled={loading}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
