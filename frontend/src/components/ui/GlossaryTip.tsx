import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { m, AnimatePresence } from '../../lib/framer';
import { displayLabel } from '../../lib/displayText';
import { useGlossary } from '../../context/GlossaryContext';
import type { GlossaryEntry } from '../../lib/glossary';
import MarkdownContent from './MarkdownContent';

interface Props {
  name: string;
  children?: ReactNode;
  className?: string;
  wrapperClassName?: string;
  variant?: 'chip' | 'inline' | 'custom';
  classId?: string;
  /** Force tooltip below or above the trigger; default picks by available space. */
  placementMode?: 'auto' | 'below' | 'above';
  /** Align tooltip with the start (left) edge of the trigger instead of centering. */
  align?: 'center' | 'start';
}

const KIND_LABEL: Record<string, string> = {
  spell: 'Spell',
  weapon: 'Weapon',
  armor: 'Armor',
  item: 'Item',
  skill: 'Skill',
  language: 'Language',
  rules: 'Rules',
  feature: 'Feature',
  feat: 'Feat',
  class: 'Class',
  species: 'Species',
  background: 'Background',
};

const TIP_WIDTH = 352;
const VIEWPORT_PAD = 10;
const GAP = 8;

interface Placement {
  left: number;
  top: number;
  maxHeight: number;
  above: boolean;
}

function computePlacement(
  trigger: DOMRect,
  placement: 'auto' | 'below' | 'above' = 'auto',
  align: 'center' | 'start' = 'center',
): Placement {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const width = Math.min(TIP_WIDTH, vw - VIEWPORT_PAD * 2);

  let left = align === 'start' ? trigger.left : trigger.left + trigger.width / 2 - width / 2;
  left = Math.max(VIEWPORT_PAD, Math.min(left, vw - width - VIEWPORT_PAD));

  const spaceAbove = trigger.top - VIEWPORT_PAD;
  const spaceBelow = vh - trigger.bottom - VIEWPORT_PAD;
  const above =
    placement === 'above' ? true : placement === 'below' ? false : spaceAbove >= 140 && spaceAbove >= spaceBelow;

  if (above) {
    const maxHeight = Math.max(120, Math.min(360, spaceAbove - GAP));
    return { left, top: trigger.top - GAP, maxHeight, above: true };
  }
  const maxHeight = Math.max(120, Math.min(360, spaceBelow - GAP));
  return { left, top: trigger.bottom + GAP, maxHeight, above: false };
}

function GlossaryEntryBody({
  entry,
  loading,
  maxHeight,
  compact = false,
}: {
  entry: GlossaryEntry | null;
  loading: boolean;
  maxHeight?: number;
  compact?: boolean;
}) {
  if (loading) {
    return <p className="text-muted italic text-xs">Looking up…</p>;
  }
  if (!entry?.summary) {
    return <p className="text-muted italic text-xs">No description available.</p>;
  }
  return (
    <>
      <p className="text-[10px] uppercase tracking-wider text-accent/80 mb-1.5 shrink-0">
        {KIND_LABEL[entry.kind] || entry.kind}
        {entry.level != null && entry.level > 0 ? ` · L${entry.level}` : entry.level === 0 ? ' · Cantrip' : ''}
      </p>
      <div
        className={`overflow-y-auto overflow-x-hidden pr-1 ${compact ? 'max-h-32' : ''}`}
        style={maxHeight ? { maxHeight: Math.max(80, maxHeight - 72) } : undefined}
      >
        <MarkdownContent content={entry.summary} className="text-xs" />
      </div>
    </>
  );
}

type GlossaryFetchState = {
  key: string;
  entry: GlossaryEntry | null;
  loading: boolean;
};

function useGlossaryEntry(name: string, classId?: string) {
  const { getEntry, fetchEntry } = useGlossary();
  const staticEntry = name ? getEntry(name, classId) : null;
  const hasStatic = Boolean(staticEntry?.summary);
  const requestKey = `${name}:${classId ?? ''}`;

  const [fetchState, setFetchState] = useState<GlossaryFetchState>({
    key: requestKey,
    entry: null,
    loading: false,
  });

  if (requestKey !== fetchState.key) {
    setFetchState({
      key: requestKey,
      entry: null,
      loading: Boolean(name && !hasStatic),
    });
  }

  useEffect(() => {
    if (!name || hasStatic || !fetchState.loading || fetchState.key !== requestKey) return;
    let cancelled = false;
    fetchEntry(name, classId).then((result) => {
      if (!cancelled) {
        setFetchState({ key: requestKey, entry: result, loading: false });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [name, classId, hasStatic, fetchEntry, requestKey, fetchState.key, fetchState.loading]);

  if (!name) return { entry: null, loading: false };
  if (hasStatic) return { entry: staticEntry, loading: false };
  return { entry: fetchState.entry, loading: fetchState.loading };
}

export default function GlossaryTip({
  name,
  children,
  className = '',
  wrapperClassName = '',
  variant = 'chip',
  classId,
  placementMode = 'auto',
  align = 'center',
}: Props) {
  const { getEntry, fetchEntry } = useGlossary();
  const [open, setOpen] = useState(false);
  const [entry, setEntry] = useState<GlossaryEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [placement, setPlacement] = useState<Placement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | HTMLSpanElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);
  const showTimerRef = useRef<number | null>(null);
  const hideTimerRef = useRef<number | null>(null);

  const updatePlacement = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    setPlacement(computePlacement(el.getBoundingClientRect(), placementMode, align));
  }, [placementMode, align]);

  const show = useCallback(async () => {
    const staticEntry = getEntry(name, classId);
    if (staticEntry?.summary) {
      setEntry(staticEntry);
      setOpen(true);
      return;
    }
    setLoading(true);
    setOpen(true);
    const fetched = await fetchEntry(name, classId);
    setEntry(fetched);
    setLoading(false);
  }, [name, classId, getEntry, fetchEntry]);

  const scheduleShow = () => {
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current);
    if (showTimerRef.current) window.clearTimeout(showTimerRef.current);
    showTimerRef.current = window.setTimeout(() => {
      show();
    }, 200);
  };

  const dismiss = () => {
    if (showTimerRef.current) window.clearTimeout(showTimerRef.current);
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current);
    setOpen(false);
    setLoading(false);
  };

  const scheduleHide = () => {
    if (showTimerRef.current) window.clearTimeout(showTimerRef.current);
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current);
    hideTimerRef.current = window.setTimeout(() => {
      setOpen(false);
      setLoading(false);
    }, 120);
  };

  const cancelHide = () => {
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current);
  };

  useEffect(() => {
    if (!open) return;
    updatePlacement();
    const onScrollOrResize = () => updatePlacement();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [open, updatePlacement, entry]);

  const label = displayLabel(name);
  const trigger =
    children ??
    (variant === 'inline' ? (
      <span className={`underline decoration-dotted decoration-muted/50 cursor-pointer ${className}`}>{label}</span>
    ) : (
      <span className={`sheet-tag cursor-pointer ${className}`}>{label}</span>
    ));

  const tip =
    open && placement
      ? createPortal(
          <AnimatePresence>
            <m.div
              ref={tipRef}
              initial={{ opacity: 0, y: placement.above ? 6 : -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: placement.above ? 6 : -6 }}
              transition={{ duration: 0.12 }}
              style={{
                position: 'fixed',
                left: placement.left,
                top: placement.top,
                width: Math.min(TIP_WIDTH, window.innerWidth - VIEWPORT_PAD * 2),
                maxHeight: placement.maxHeight,
                transform: placement.above ? 'translateY(-100%)' : undefined,
                zIndex: 9999,
              }}
              className="flex flex-col p-3 panel-glow shadow-glow pointer-events-none"
            >
              <p className="font-medium text-accent text-sm mb-1.5 shrink-0">{displayLabel(entry?.title || name)}</p>
              <GlossaryEntryBody entry={entry} loading={loading} maxHeight={placement.maxHeight} />
            </m.div>
          </AnimatePresence>,
          document.body,
        )
      : null;

  const triggerHandlers = {
    onMouseEnter: () => {
      cancelHide();
      scheduleShow();
    },
    onMouseLeave: scheduleHide,
    onMouseDown: dismiss,
    onFocus: () => {
      cancelHide();
      show();
    },
    onBlur: scheduleHide,
  };

  return (
    <>
      {children ? (
        <span
          ref={triggerRef as RefObject<HTMLSpanElement>}
          className={`relative inline-block group/gtip ${wrapperClassName}`}
          {...triggerHandlers}
        >
          {trigger}
        </span>
      ) : (
        <button
          ref={triggerRef as RefObject<HTMLButtonElement>}
          type="button"
          className={`relative inline-block group/gtip border-0 bg-transparent p-0 font-inherit text-inherit ${wrapperClassName}`}
          {...triggerHandlers}
          aria-label={`${label}, hover for details`}
        >
          {trigger}
        </button>
      )}
      {tip}
    </>
  );
}

export function GlossaryTagList({
  items,
  className = '',
  classId,
}: {
  items: string[];
  className?: string;
  classId?: string;
}) {
  if (!items.length) return <span className="text-sm text-muted">-</span>;
  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`}>
      {items.map((item) => (
        <GlossaryTip key={item} name={item} classId={classId} />
      ))}
    </div>
  );
}
