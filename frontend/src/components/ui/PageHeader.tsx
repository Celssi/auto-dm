import type { ReactNode } from 'react';
import { m } from '../../lib/framer';
import { fadeUp } from './motion';

interface Props {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export default function PageHeader({ title, subtitle, actions }: Props) {
  return (
    <m.header variants={fadeUp} className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="font-display text-2xl md:text-3xl font-semibold text-gradient">{title}</h1>
        {subtitle && <p className="text-sm text-muted mt-1.5 max-w-2xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
    </m.header>
  );
}
