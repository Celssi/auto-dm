import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, Home, MoreHorizontal, Play, ScrollText, Settings, Users } from 'lucide-react';

const primary = [
  { to: '/', label: 'Home', icon: Home, exact: true },
  { to: '/characters', label: 'Characters', icon: Users },
  { to: '/campaigns', label: 'Campaigns', icon: BookOpen },
  { to: '/play', label: 'Play', icon: Play },
];

const moreLinks = [
  { to: '/adventures', label: 'Adventures', icon: ScrollText },
  { to: '/settings', label: 'Settings', icon: Settings },
];

function isActive(pathname: string, to: string, exact?: boolean) {
  if (exact) return pathname === to;
  return pathname.startsWith(to);
}

export default function BottomNav() {
  const { pathname } = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreActive = moreLinks.some((link) => isActive(pathname, link.to));

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 border-t border-border/80 bg-panel/95 backdrop-blur-md pb-[env(safe-area-inset-bottom)]">
      {moreOpen && (
        <div className="border-b border-border/80 px-3 py-2 grid grid-cols-2 gap-2">
          {moreLinks.map(({ to, label, icon: Icon }) => {
            const active = isActive(pathname, to);
            return (
              <Link
                key={to}
                to={to}
                onClick={() => setMoreOpen(false)}
                className={`min-h-11 inline-flex items-center justify-center gap-2 rounded-xl text-sm ${
                  active ? 'bg-accent/10 text-accent' : 'text-muted'
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </div>
      )}
      <div className="grid grid-cols-5">
        {primary.map(({ to, label, icon: Icon, exact }) => {
          const active = isActive(pathname, to, exact);
          return (
            <Link
              key={to}
              to={to}
              className={`min-h-14 flex flex-col items-center justify-center gap-0.5 text-[11px] ${
                active ? 'text-accent' : 'text-muted'
              }`}
            >
              <Icon size={20} />
              {label}
            </Link>
          );
        })}
        <button
          type="button"
          className={`min-h-14 flex flex-col items-center justify-center gap-0.5 text-[11px] ${
            moreOpen || moreActive ? 'text-accent' : 'text-muted'
          }`}
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((value) => !value)}
        >
          <MoreHorizontal size={20} />
          More
        </button>
      </div>
    </nav>
  );
}
