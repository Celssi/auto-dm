interface Props {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
}

export default function Toggle({ checked, onChange, label, description }: Props) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <span className="relative shrink-0 mt-0.5 w-10 h-5">
        <input
          type="checkbox"
          role="switch"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <span
          aria-hidden
          className={`block w-10 h-5 rounded-full border transition-colors ${
            checked ? 'bg-accent/80 border-accent' : 'bg-bg border-border group-hover:border-accent/40'
          }`}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
              checked ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </span>
      </span>
      <span className="min-w-0">
        <span className="text-sm text-gray-200 group-hover:text-white transition-colors">{label}</span>
        {description && <span className="block text-xs text-muted mt-0.5 leading-relaxed">{description}</span>}
      </span>
    </label>
  );
}
