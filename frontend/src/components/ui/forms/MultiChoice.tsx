import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { displayLabel, normalizeChoiceId } from '../../../lib/displayText';
import GlossaryTip from '../GlossaryTip';
import TextInput from './TextInput';

interface Props {
  value: string[];
  onChange: (value: string[]) => void;
  options: string[];
  max?: number;
  searchable?: boolean;
  searchPlaceholder?: string;
}

function chipClass(active: boolean, disabled: boolean) {
  if (disabled) return 'border-border/50 bg-bg/20 text-muted cursor-not-allowed opacity-50';
  return active
    ? 'border-accent/50 bg-accent/15 text-accent'
    : 'border-border bg-bg/40 text-gray-300 hover:border-accent/30 hover:bg-bg/60';
}

export default function MultiChoice({
  value,
  onChange,
  options,
  max,
  searchable = options.length > 12,
  searchPlaceholder = 'Search…',
}: Props) {
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) => o.toLowerCase().includes(q));
  }, [options, query]);

  const toggle = (item: string) => {
    const key = normalizeChoiceId(item);
    const existing = value.find((v) => normalizeChoiceId(v) === key);
    if (existing) {
      onChange(value.filter((v) => normalizeChoiceId(v) !== key));
      return;
    }
    if (max != null && value.length >= max) return;
    onChange([...value, item]);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted">
        <span>
          {value.length}
          {max != null ? ` / ${max}` : ''} selected
        </span>
        {value.length > 0 && (
          <button type="button" className="text-accent hover:underline" onClick={() => onChange([])}>
            Clear
          </button>
        )}
      </div>

      {searchable && (
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
          <TextInput
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchPlaceholder}
            className="pl-9"
          />
        </div>
      )}

      <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto rounded-lg border border-border bg-bg/30 p-2">
        {filtered.length === 0 && <p className="text-xs text-muted px-1 py-2">No matches.</p>}
        {filtered.map((item) => {
          const active = value.some((v) => normalizeChoiceId(v) === normalizeChoiceId(item));
          const atMax = max != null && !active && value.length >= max;
          return (
            <GlossaryTip key={item} name={item} variant="custom" placementMode="below" align="start">
              <button
                type="button"
                disabled={atMax}
                onClick={() => toggle(item)}
                className={`text-xs px-2.5 py-1.5 rounded-full border transition-colors cursor-pointer ${chipClass(active, !!atMax)}`}
              >
                {displayLabel(item)}
              </button>
            </GlossaryTip>
          );
        })}
      </div>
    </div>
  );
}
