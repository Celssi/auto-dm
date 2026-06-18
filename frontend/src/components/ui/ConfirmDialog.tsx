import { m, AnimatePresence } from '../../lib/framer';

interface Props {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  onConfirm,
  onCancel,
  busy = false,
}: Props) {
  return (
    <AnimatePresence>
      {open && (
        <m.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/80 backdrop-blur-sm"
          onClick={onCancel}
        >
          <m.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            className="panel-glow w-full max-w-md p-5 space-y-4"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
          >
            <h2 id="confirm-dialog-title" className="font-display text-lg text-gray-100">
              {title}
            </h2>
            <p className="text-sm text-muted leading-relaxed">{message}</p>
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" className="btn-ghost" onClick={onCancel} disabled={busy}>
                Cancel
              </button>
              <button type="button" className="btn-danger" onClick={onConfirm} disabled={busy}>
                {busy ? 'Deleting…' : confirmLabel}
              </button>
            </div>
          </m.div>
        </m.div>
      )}
    </AnimatePresence>
  );
}
