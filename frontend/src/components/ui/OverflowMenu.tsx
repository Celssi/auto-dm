import { useEffect, useRef, useState, type ReactNode } from 'react';
import { MoreHorizontal } from 'lucide-react';

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
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="btn-ghost min-h-11 px-3 inline-flex items-center gap-1.5"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {children ?? <MoreHorizontal size={16} />}
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-1 z-30 min-w-[12rem] rounded-xl border border-border bg-panel p-1 shadow-lg"
        >
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              className={`w-full text-left rounded-lg px-3 py-2 text-sm min-h-11 ${
                item.danger ? 'text-danger hover:bg-danger/10' : 'text-gray-100 hover:bg-accent/10'
              }`}
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
