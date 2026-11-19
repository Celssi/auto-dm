interface Props {
  oracles: { id: string; label: string; help?: string }[];
  loading: boolean;
  onRun: (id: string) => void;
}

export default function PlayOracleGrid({ oracles, loading, onRun }: Props) {
  return (
    <div className="shrink-0">
      <h2 className="section-heading mb-1.5">Oracles</h2>
      <p className="text-[11px] text-muted leading-relaxed mb-1.5">
        Yes/no and spark answers. They do not invent the story.
      </p>
      <div className="grid grid-cols-2 gap-1 max-h-[9rem] overflow-y-auto pr-0.5">
        {oracles.map((o) => (
          <button
            key={o.id}
            type="button"
            className="play-chip text-left"
            onClick={() => onRun(o.id)}
            disabled={loading}
            title={o.help || o.label}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}
