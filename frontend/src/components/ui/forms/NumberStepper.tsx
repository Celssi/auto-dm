interface StepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  label?: string;
}

export default function NumberStepper({ value, onChange, min = 0, max = 2, label }: StepperProps) {
  return (
    <div className="flex items-center gap-1">
      {label && <span className="text-xs uppercase text-muted w-8">{label}</span>}
      {Array.from({ length: max - min + 1 }, (_, i) => min + i).map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={`w-8 h-8 rounded-md text-xs font-medium border transition-colors ${
            value === n
              ? 'border-accent/50 bg-accent/15 text-accent'
              : 'border-border bg-bg/40 text-muted hover:border-accent/30'
          }`}
        >
          {n === 0 ? '-' : `+${n}`}
        </button>
      ))}
    </div>
  );
}
