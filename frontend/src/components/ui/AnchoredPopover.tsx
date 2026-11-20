import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
  type RefObject,
} from 'react';
import { createPortal } from 'react-dom';

const MENU_Z = 60;
const VIEWPORT_PAD = 8;
const GAP = 4;

type Props = {
  open: boolean;
  triggerRef: RefObject<HTMLElement | null>;
  onClose: () => void;
  children: ReactNode;
  className?: string;
  role?: string;
  align?: 'start' | 'end';
};

/** Fixed, portaled menu so it stacks above tooltip labels and page cards. */
export default function AnchoredPopover({
  open,
  triggerRef,
  onClose,
  children,
  className = '',
  role,
  align = 'end',
}: Props) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<CSSProperties>({ position: 'fixed', zIndex: MENU_Z });

  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const trigger = triggerRef.current;
      const menu = menuRef.current;
      if (!trigger) return;
      const r = trigger.getBoundingClientRect();
      const width = menu?.offsetWidth || 192;
      const height = menu?.offsetHeight || 0;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      let left = align === 'end' ? r.right - width : r.left;
      left = Math.max(VIEWPORT_PAD, Math.min(left, vw - width - VIEWPORT_PAD));
      let top = r.bottom + GAP;
      if (height && top + height > vh - VIEWPORT_PAD) {
        top = Math.max(VIEWPORT_PAD, r.top - GAP - height);
      }
      setStyle({ position: 'fixed', top, left, zIndex: MENU_Z });
    };
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
    };
  }, [open, triggerRef, align]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (triggerRef.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      onClose();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open, onClose, triggerRef]);

  if (!open || typeof document === 'undefined') return null;
  return createPortal(
    <div ref={menuRef} role={role} style={style} className={className}>
      {children}
    </div>,
    document.body,
  );
}
