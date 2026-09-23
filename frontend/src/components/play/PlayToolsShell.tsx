import type { ReactNode } from 'react';

export default function PlayToolsShell({ children }: { children: ReactNode }) {
  return <aside className="lg:col-span-3 panel-glow overflow-hidden p-3 min-h-0 flex flex-col gap-2">{children}</aside>;
}
