interface SegmentedProps {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}

export default function SegmentedControl({ value, onChange, options }: SegmentedProps) {
  return (
    <div className="flex flex-wrap gap-1.5 p-1 rounded-xl bg-bg/50 border border-border w-fit">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`text-sm min-h-11 px-3 rounded-lg transition-colors ${
            value === opt.value
              ? 'bg-accent/15 text-accent border border-accent/25'
              : 'text-muted hover:text-gray-200 border border-transparent'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
