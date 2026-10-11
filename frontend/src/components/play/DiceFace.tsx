import { useEffect, useState } from 'react';
import { m } from '../../lib/framer';

export default function DiceFace({
  value,
  rolling,
  chosen,
  dimmed,
}: {
  value: number | null;
  rolling: boolean;
  chosen?: boolean;
  dimmed?: boolean;
}) {
  const [rollingFace, setRollingFace] = useState(value ?? 20);
  const display = !rolling && value != null ? value : rollingFace;

  useEffect(() => {
    if (!rolling) return;
    const intervalId = setInterval(() => {
      setRollingFace(Math.floor(Math.random() * 20) + 1);
    }, 60);
    return () => clearInterval(intervalId);
  }, [rolling]);

  return (
    <m.div
      className={`relative flex items-center justify-center w-20 h-20 rounded-lg border-2 font-display text-3xl tabular-nums select-none transition-colors ${
        dimmed
          ? 'border-border/40 text-muted bg-bg/30'
          : chosen
            ? 'border-accent text-accent bg-accent/10 shadow-glow-sm'
            : 'border-border text-gray-100 bg-bg/60'
      }`}
      animate={
        !rolling && value != null ? { scale: [1.15, 1], transition: { duration: 0.3, ease: 'easeOut' } } : undefined
      }
    >
      {display}
      <span className="absolute -bottom-5 text-[10px] text-muted">d20</span>
    </m.div>
  );
}
