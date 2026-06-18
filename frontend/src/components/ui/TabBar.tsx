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
    <div className="flex gap-1 p-1 rounded-lg bg-bg/60 border border-border/60 w-fit">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`relative text-sm px-4 py-1.5 rounded-md transition-colors ${
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
  );
}
