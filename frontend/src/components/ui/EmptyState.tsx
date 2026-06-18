import type { ReactNode } from 'react';
import { m } from '../../lib/framer';
import { fadeUp } from './motion';

interface Props {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export default function EmptyState({ icon, title, description, action }: Props) {
  return (
    <m.div variants={fadeUp} className="panel-glow p-10 text-center flex flex-col items-center">
      {icon && <div className="text-accent/60 mb-4">{icon}</div>}
      <p className="font-medium text-gray-200">{title}</p>
      {description && <p className="text-sm text-muted mt-2 max-w-sm">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </m.div>
  );
}
