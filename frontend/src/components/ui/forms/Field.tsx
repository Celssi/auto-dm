import type { ReactNode } from 'react';

interface Props {
  label?: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}

export function Field({ label, hint, children, className = '' }: Props) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && <span className="label-text block">{label}</span>}
      {children}
      {hint && <p className="text-xs text-muted leading-relaxed">{hint}</p>}
    </div>
  );
}
