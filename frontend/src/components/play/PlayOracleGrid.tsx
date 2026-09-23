interface Props {
  oracles: { id: string; label: string }[];
  loading: boolean;
  onRun: (id: string) => void;
}

export default function PlayOracleGrid({ oracles, loading, onRun }: Props) {
  return (
    <div className="shrink-0">
      <h2 className="section-heading mb-1.5">Oracles</h2>
      <div className="grid grid-cols-2 gap-1 max-h-[9rem] overflow-y-auto pr-0.5">
        {oracles.map((o) => (
          <button
            key={o.id}
            type="button"
            className="play-chip text-left"
            onClick={() => onRun(o.id)}
            disabled={loading}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}
