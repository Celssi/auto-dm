import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { m, AnimatePresence } from '../../lib/framer';
import { formatJournalBody, type JournalEntity } from '../../lib/journalTips';
import MarkdownContent from '../ui/MarkdownContent';

const KIND_LABEL: Record<string, string> = {
  npc: 'NPC',
  location: 'Location',
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

function computePlacement(trigger: DOMRect): Placement {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const width = Math.min(TIP_WIDTH, vw - VIEWPORT_PAD * 2);

  let left = trigger.left + trigger.width / 2 - width / 2;
  left = Math.max(VIEWPORT_PAD, Math.min(left, vw - width - VIEWPORT_PAD));

  const spaceAbove = trigger.top - VIEWPORT_PAD;
  const spaceBelow = vh - trigger.bottom - VIEWPORT_PAD;
  const above = spaceAbove >= 140 || spaceAbove >= spaceBelow;

  if (above) {
    const maxHeight = Math.max(120, Math.min(360, spaceAbove - GAP));
    return { left, top: trigger.top - GAP, maxHeight, above: true };
  }
  const maxHeight = Math.max(120, Math.min(360, spaceBelow - GAP));
  return { left, top: trigger.bottom + GAP, maxHeight, above: false };
}

interface Props {
  entity: JournalEntity;
  text: string;
}

export default function JournalTip({ entity, text }: Props) {
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState<Placement | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const showTimerRef = useRef<number | null>(null);
  const hideTimerRef = useRef<number | null>(null);

  const updatePlacement = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    setPlacement(computePlacement(el.getBoundingClientRect()));
  }, []);

  const scheduleShow = () => {
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current);
    if (showTimerRef.current) window.clearTimeout(showTimerRef.current);
    showTimerRef.current = window.setTimeout(() => setOpen(true), 200);
  };

  const scheduleHide = () => {
    if (showTimerRef.current) window.clearTimeout(showTimerRef.current);
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current);
    hideTimerRef.current = window.setTimeout(() => setOpen(false), 120);
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
  }, [open, updatePlacement]);

  const body = formatJournalBody(entity.body);

  const tip =
    open && placement
      ? createPortal(
          <AnimatePresence>
            <m.div
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
              className="flex flex-col p-3 panel-glow shadow-glow pointer-events-auto"
              onMouseEnter={cancelHide}
              onMouseLeave={scheduleHide}
            >
              <p className="font-medium text-accent text-sm mb-1.5 shrink-0">{entity.name}</p>
              <p className="text-[10px] uppercase tracking-wider text-accent/80 mb-1.5 shrink-0">
                {KIND_LABEL[entity.kind] || entity.kind}
              </p>
              {body.trim() ? (
                <div
                  className="overflow-y-auto overflow-x-hidden pr-1"
                  style={{ maxHeight: Math.max(80, placement.maxHeight - 72) }}
                >
                  <MarkdownContent content={body} className="text-xs" />
                </div>
              ) : (
                <p className="text-muted italic text-xs">No journal entry yet.</p>
              )}
            </m.div>
          </AnimatePresence>,
          document.body,
        )
      : null;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="border-0 bg-transparent p-0 font-inherit text-inherit underline decoration-dotted decoration-accent/40 cursor-help"
        onMouseEnter={() => {
          cancelHide();
          scheduleShow();
        }}
        onMouseLeave={scheduleHide}
        onFocus={() => {
          cancelHide();
          setOpen(true);
        }}
        onBlur={scheduleHide}
        aria-label={`${entity.name}, ${KIND_LABEL[entity.kind] || entity.kind}`}
      >
        {text}
      </button>
      {tip}
    </>
  );
}
