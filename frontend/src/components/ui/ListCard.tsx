import type { ReactNode } from 'react';
import { m } from '../../lib/framer';
import { displayLabel } from '../../lib/displayText';
import { fadeUp } from './motion';

interface Props {
  title: string;
  subtitle?: string;
  onClick?: () => void;
  selected?: boolean;
  children?: ReactNode;
}

export default function ListCard({ title, subtitle, onClick, selected, children }: Props) {
  const Tag = onClick ? m.button : m.div;
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      variants={fadeUp}
      whileHover={onClick ? { y: -2, transition: { duration: 0.15 } } : undefined}
      whileTap={onClick ? { scale: 0.99 } : undefined}
      onClick={onClick}
      className={`panel w-full text-left p-4 transition-colors ${
        selected ? 'border-accent/50 bg-accent/5 shadow-glow-sm' : 'hover:border-accent/30 hover:bg-panel-hover'
      }`}
    >
      <div className="font-medium text-gray-100">{title}</div>
      {subtitle && <div className="text-xs text-muted mt-0.5">{displayLabel(subtitle)}</div>}
      {children}
    </Tag>
  );
}
