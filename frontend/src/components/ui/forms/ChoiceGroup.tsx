import { displayLabel } from '../../../lib/displayText';
import GlossaryTip from '../GlossaryTip';

interface Option {
  value: string;
  label: string;
}

interface Group {
  label: string;
  options: Option[];
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  options?: Option[];
  groups?: Group[];
  allowEmpty?: boolean;
  emptyLabel?: string;
  columns?: 2 | 3 | 4;
}

const EMPTY_OPTIONS: Option[] = [];

function chipClass(active: boolean) {
  return active
    ? 'border-accent/50 bg-accent/15 text-accent shadow-glow-sm'
    : 'border-border bg-bg/40 text-gray-300 hover:border-accent/30 hover:bg-bg/60';
}

function optionLabel(opt: Option) {
  return opt.label !== opt.value ? opt.label : displayLabel(opt.label);
}

function ChoiceOptionGrid({
  opts,
  value,
  onChange,
  allowEmpty,
  emptyLabel,
  colClass,
}: {
  opts: Option[];
  value: string;
  onChange: (value: string) => void;
  allowEmpty: boolean;
  emptyLabel: string;
  colClass: string;
}) {
  return (
    <div className={`grid ${colClass} gap-1.5`}>
      {allowEmpty && (
        <button
          type="button"
          onClick={() => onChange('')}
          className={`text-left text-sm px-3 py-2 rounded-lg border transition-colors ${chipClass(value === '')}`}
        >
          {emptyLabel}
        </button>
      )}
      {opts.map((opt) => (
        <GlossaryTip
          key={opt.value}
          name={opt.value}
          variant="custom"
          wrapperClassName="block w-full"
          placementMode="below"
          align="start"
        >
          <button
            type="button"
            onClick={() => onChange(opt.value)}
            className={`w-full text-left text-sm px-3 py-2 rounded-lg border transition-colors cursor-pointer ${chipClass(value === opt.value)}`}
          >
            {optionLabel(opt)}
          </button>
        </GlossaryTip>
      ))}
    </div>
  );
}

export default function ChoiceGroup({
  value,
  onChange,
  options = EMPTY_OPTIONS,
  groups,
  allowEmpty = false,
  emptyLabel = 'None',
  columns = 3,
}: Props) {
  const colClass =
    columns === 2 ? 'grid-cols-2' : columns === 4 ? 'grid-cols-2 sm:grid-cols-4' : 'grid-cols-2 sm:grid-cols-3';

  if (groups?.length) {
    return (
      <div className="space-y-4">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="text-[10px] uppercase tracking-wider text-muted mb-2">{group.label}</p>
            <ChoiceOptionGrid
              opts={group.options}
              value={value}
              onChange={onChange}
              allowEmpty={allowEmpty}
              emptyLabel={emptyLabel}
              colClass={colClass}
            />
          </div>
        ))}
      </div>
    );
  }

  return (
    <ChoiceOptionGrid
      opts={options}
      value={value}
      onChange={onChange}
      allowEmpty={allowEmpty}
      emptyLabel={emptyLabel}
      colClass={colClass}
    />
  );
}
