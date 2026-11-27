import { useRef, useState, type ReactNode } from 'react';
import { MoreHorizontal } from 'lucide-react';
import AnchoredPopover from './AnchoredPopover';

export type OverflowMenuItem = {
  label: string;
  onSelect: () => void;
  danger?: boolean;
};

interface Props {
  items: OverflowMenuItem[];
  label?: string;
  children?: ReactNode;
}

export default function OverflowMenu({ items, label = 'More actions', children }: Props) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const close = () => {
    setOpen(false);
    triggerRef.current?.focus();
  };

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        className="btn-ghost min-h-11 min-w-11 px-3 inline-flex justify-center items-center gap-1.5"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {children ?? <MoreHorizontal size={16} />}
      </button>
      <AnchoredPopover open={open} triggerRef={triggerRef} onClose={close} role="menu" className="sheet-menu">
        {items.map((item) => (
          <button
            key={item.label}
            type="button"
            role="menuitem"
            className={`sheet-menu-item ${item.danger ? 'sheet-menu-item-danger' : ''}`}
            onClick={() => {
              setOpen(false);
              item.onSelect();
            }}
          >
            {item.label}
          </button>
        ))}
      </AnchoredPopover>
    </div>
  );
}
