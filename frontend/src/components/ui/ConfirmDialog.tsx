import { useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { m, AnimatePresence } from '../../lib/framer';
import { useFocusTrap } from '../../hooks/useFocusTrap';

interface Props {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}

export default function ConfirmDialog(props: Props) {
  return createPortal(
    <AnimatePresence>{props.open && <ConfirmDialogBody {...props} />}</AnimatePresence>,
    document.body,
  );
}

function ConfirmDialogBody({ title, message, confirmLabel = 'Delete', onConfirm, onCancel, busy = false }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const messageId = useId();
  // Cancel gets initial focus so Enter never confirms a destructive action by accident.
  useFocusTrap(dialogRef, true, busy ? undefined : onCancel, cancelRef);

  return (
    <m.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/80 backdrop-blur-sm"
      onClick={busy ? undefined : onCancel}
    >
      <m.div
        ref={dialogRef}
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        className="panel-glow w-full max-w-md p-5 space-y-4"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={messageId}
        tabIndex={-1}
      >
        <h2 id={titleId} className="display-title text-lg">
          {title}
        </h2>
        <p id={messageId} className="text-sm text-muted leading-relaxed">
          {message}
        </p>
        <div className="flex flex-wrap justify-end gap-2 pt-1">
          <button ref={cancelRef} type="button" className="btn-ghost min-h-11" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="button" className="btn-danger min-h-11" onClick={onConfirm} disabled={busy}>
            {busy ? 'Deleting…' : confirmLabel}
          </button>
        </div>
      </m.div>
    </m.div>
  );
}
