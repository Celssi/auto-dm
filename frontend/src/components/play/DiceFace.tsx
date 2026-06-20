import { useEffect, useRef, useState } from 'react';
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
  const [display, setDisplay] = useState(value ?? 20);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!rolling) {
      if (value != null) setDisplay(value);
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(() => {
      setDisplay(Math.floor(Math.random() * 20) + 1);
    }, 60);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [rolling, value]);

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
