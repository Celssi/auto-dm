import { m } from '../../lib/framer';

interface Tab {
  id: string;
  label: string;
}

interface Props {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
}

export default function TabBar({ tabs, active, onChange }: Props) {
  return (
    <div className="max-w-full overflow-x-auto scrollbar-none">
      <div role="tablist" className="flex gap-1 p-1 rounded-xl bg-bg/60 border border-border/60 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active === tab.id}
            onClick={() => onChange(tab.id)}
            className={`relative shrink-0 whitespace-nowrap text-sm min-h-11 px-3 sm:px-4 rounded-lg transition-colors ${
              active === tab.id ? 'text-accent' : 'text-muted hover:text-gray-200'
            }`}
          >
            {active === tab.id && (
              <m.span
                layoutId="tab-indicator"
                className="absolute inset-0 bg-accent/15 border border-accent/25 rounded-md"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative z-10">{tab.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
