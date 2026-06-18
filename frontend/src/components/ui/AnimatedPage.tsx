import type { ReactNode } from 'react';
import { m } from '../../lib/framer';
import { staggerContainer } from './motion';
import { useStaggerInitial } from './usePageMotion';

export default function AnimatedPage({ children, className = '' }: { children: ReactNode; className?: string }) {
  const initial = useStaggerInitial();

  return (
    <m.div variants={staggerContainer} initial={initial} animate="animate" className={className}>
      {children}
    </m.div>
  );
}
