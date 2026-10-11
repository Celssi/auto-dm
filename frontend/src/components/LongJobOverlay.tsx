import { LoaderCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useKeepAlive } from '../hooks/useKeepAlive';

function formatElapsed(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins < 1) return `${secs}s`;
  return `${mins}m ${secs.toString().padStart(2, '0')}s`;
}

interface Props {
  active: boolean;
  title: string;
  message?: string;
}

export default function LongJobOverlay({ active, title, message }: Props) {
  const [elapsed, setElapsed] = useState(0);
  useKeepAlive(active);

  useEffect(() => {
    if (!active) {
      setElapsed(0);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [active]);

  if (!active) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 backdrop-blur-sm px-4">
      <div className="panel-glow w-full max-w-md p-6 space-y-4 text-center">
        <LoaderCircle className="mx-auto text-accent animate-spin" size={28} />
        <div className="space-y-1">
          <h2 className="display-title text-lg">{title}</h2>
          <p className="text-sm text-muted">
            {message || 'This window stays open so Cloud Run does not scale away mid-job.'}
          </p>
        </div>
        <p className="text-xs text-muted">Elapsed {formatElapsed(elapsed)}. Keep this tab in the foreground.</p>
      </div>
    </div>
  );
}
