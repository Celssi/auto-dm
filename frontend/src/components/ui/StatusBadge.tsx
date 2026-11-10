import { m } from '../../lib/framer';
import { CheckCircle2, AlertCircle, Loader2, XCircle } from 'lucide-react';

type Status = 'ok' | 'warn' | 'error' | 'pending';

const styles: Record<Status, string> = {
  ok: 'border-success/30 bg-success/10 text-success',
  warn: 'border-warning/30 bg-warning/10 text-warning',
  error: 'border-danger/30 bg-danger/10 text-danger',
  pending: 'border-border bg-bg/40 text-muted',
};

const icons: Record<Status, typeof CheckCircle2> = {
  ok: CheckCircle2,
  warn: AlertCircle,
  error: XCircle,
  pending: Loader2,
};

export default function StatusBadge({ status, label }: { status: Status; label: string }) {
  const Icon = icons[status];
  return (
    <m.span
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      role={status === 'pending' ? 'status' : undefined}
      className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${styles[status]}`}
    >
      <Icon size={13} aria-hidden="true" className={status === 'pending' ? 'animate-spin' : undefined} />
      {label}
    </m.span>
  );
}
