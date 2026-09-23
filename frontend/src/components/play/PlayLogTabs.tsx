import type { ReactNode } from 'react';

export type PlayLogTab = 'lonelog' | 'audit' | 'journey' | 'deck' | 'dragonkeep' | 'combat';

const TAB_LABELS: Record<PlayLogTab, string> = {
  lonelog: 'Lonelog',
  audit: 'Audit',
  journey: 'Journey',
  deck: 'Deck',
  dragonkeep: 'Dragonkeep',
  combat: 'Combat',
};

interface Props {
  tabs: PlayLogTab[];
  active: PlayLogTab;
  onChange: (tab: PlayLogTab) => void;
  children: ReactNode;
}

export default function PlayLogTabs({ tabs, active, onChange, children }: Props) {
  return (
    <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 mb-1.5 shrink-0 flex-wrap">
        {tabs.map((tab, i) => (
          <span key={tab} className="flex items-center gap-2">
            {i > 0 && <span className="text-muted text-xs">|</span>}
            <button
              type="button"
              className={`text-xs font-semibold uppercase tracking-wider ${
                active === tab ? 'text-accent' : 'text-muted hover:text-accent/70'
              }`}
              onClick={() => onChange(tab)}
            >
              {TAB_LABELS[tab]}
            </button>
          </span>
        ))}
      </div>
      <div className="flex-1 min-h-0 rounded-md border border-border bg-bg/40 p-2 overflow-y-auto">{children}</div>
    </div>
  );
}
