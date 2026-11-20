import type { ReactNode } from 'react';
import GlossaryTip from './GlossaryTip';
import { beginnerTip } from '../../lib/beginnerTips';

interface Props {
  id: string;
  /** Override the glossary lookup / title. Defaults to the beginner tip title. */
  name?: string;
  children?: ReactNode;
  className?: string;
  variant?: 'chip' | 'inline' | 'custom';
  wrapperClassName?: string;
}

/** Hover/focus explanation. Uses the in-app glossary when present, else a short beginner tip. */
export default function HelpTip({
  id,
  name,
  children,
  className = '',
  variant = 'custom',
  wrapperClassName = '',
}: Props) {
  const tip = beginnerTip(id);
  const label = name || tip?.title || id;
  return (
    <GlossaryTip
      name={label}
      variant={variant}
      className={className}
      wrapperClassName={wrapperClassName}
      fallbackSummary={tip?.summary}
      fallbackKind={tip?.kind || 'rules'}
    >
      {children}
    </GlossaryTip>
  );
}

/** Dotted label that opens a beginner tip. */
export function LabelWithTip({
  id,
  label,
  className = 'sheet-label',
  wrapperClassName = '',
}: {
  id: string;
  label: string;
  className?: string;
  wrapperClassName?: string;
}) {
  return (
    <HelpTip id={id} name={label} wrapperClassName={wrapperClassName}>
      <span
        className={`${className} cursor-help underline decoration-dotted decoration-muted/50 underline-offset-2`}
      >
        {label}
      </span>
    </HelpTip>
  );
}
