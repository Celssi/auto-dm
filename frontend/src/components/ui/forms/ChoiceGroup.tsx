import { type ReactNode } from 'react';
import { displayLabel } from '../../../lib/displayText';
import GlossaryTip from '../GlossaryTip';
import { isLikelyEntityId } from '../../../lib/glossary';

interface Option {
  value: string;
  label: string;
  /** Override glossary lookup key (defaults to value when it is a game slug). */
  glossaryName?: string;
  /** Force glossary on/off for this option. */
  glossary?: boolean;
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

function shouldShowGlossary(opt: Option): boolean {
  if (opt.glossary === false) return false;
  if (opt.glossaryName) return true;
  if (isLikelyEntityId(opt.value)) return false;
  return true;
}

function glossaryNameFor(opt: Option): string {
  if (opt.glossaryName) return opt.glossaryName;
  return opt.value;
}

function ChoiceChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left text-sm px-3 py-2 rounded-lg border transition-colors cursor-pointer ${chipClass(active)}`}
    >
      {children}
    </button>
  );
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
      {opts.map((opt) => {
        const chip = (
          <ChoiceChip active={value === opt.value} onClick={() => onChange(opt.value)}>
            {optionLabel(opt)}
          </ChoiceChip>
        );
        if (!shouldShowGlossary(opt)) {
          return (
            <div key={opt.value} className="block w-full">
              {chip}
            </div>
          );
        }
        return (
          <GlossaryTip
            key={opt.value}
            name={glossaryNameFor(opt)}
            variant="custom"
            wrapperClassName="block w-full"
            placementMode="below"
            align="start"
          >
            {chip}
          </GlossaryTip>
        );
      })}
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
            <p className="label-text mb-2">{group.label}</p>
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
