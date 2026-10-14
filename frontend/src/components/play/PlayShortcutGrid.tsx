import type { Shortcut } from '../../api/client';
import ShortcutGroups from '../../games/brambletrek/ShortcutGroups';

const DND_GROUPS: { title: string; ids: string[] }[] = [
  { title: 'Checks', ids: ['ability_check', 'saving_throw', 'attack_roll', 'initiative'] },
  { title: 'Combat', ids: ['death_save', 'cast_spell', 'lucky', 'savage_attacker', 'healer_medic'] },
  { title: 'Rest', ids: ['short_rest', 'long_rest'] },
  { title: 'Features', ids: ['oracle', 'rules_help'] },
];

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

  const groups = groupedShortcuts(shortcuts, DND_GROUPS);

  return (
    <div className="shrink-0">
      <h2 className="section-heading mb-1.5">Shortcuts</h2>
      <div className="space-y-2.5">
        {groups.map((group) => (
          <div key={group.title}>
            <p className="text-[10px] uppercase tracking-wider text-muted mb-1">{group.title}</p>
            <div className="grid grid-cols-2 gap-1">
              {group.items.map((s) => (
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
        ))}
      </div>
    </div>
  );
}

function groupedShortcuts(shortcuts: Shortcut[], groups: { title: string; ids: string[] }[]) {
  const byId = new Map(shortcuts.map((item) => [item.id, item]));
  const used = new Set<string>();
  const result = groups.flatMap((group) => {
    const items = group.ids.flatMap((id) => {
      const item = byId.get(id);
      return item ? [item] : [];
    });
    items.forEach((item) => used.add(item.id));
    return items.length > 0 ? [{ title: group.title, items }] : [];
  });
  const rest = shortcuts.filter((item) => !used.has(item.id));
  if (rest.length) result.push({ title: 'Other', items: rest });
  return result;
}
