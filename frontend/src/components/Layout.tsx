import { Link, Outlet, useLocation } from 'react-router-dom';
import { m } from '../lib/framer';
import { Dices } from 'lucide-react';

const links = [
  { to: '/', label: 'Home', exact: true },
  { to: '/characters', label: 'Characters' },
  { to: '/campaigns', label: 'Campaigns' },
  { to: '/adventures', label: 'Adventures' },
  { to: '/play', label: 'Play' },
  { to: '/settings', label: 'Settings' },
];

function isActive(pathname: string, to: string, exact?: boolean) {
  if (exact) return pathname === to;
  return pathname.startsWith(to);
}

export default function Layout() {
  const loc = useLocation();
  const isPlaySession = /^\/play\/[^/]+/.test(loc.pathname);

  return (
    <div className={`flex flex-col ${isPlaySession ? 'min-h-screen lg:h-screen lg:overflow-hidden' : 'min-h-screen'}`}>
      <nav className="border-b border-border/80 bg-panel/70 backdrop-blur-md shrink-0 z-20">
        <div
          className={`mx-auto px-4 py-3 flex items-center gap-4 md:gap-6 ${isPlaySession ? 'max-w-[1600px]' : 'max-w-7xl'}`}
        >
          <Link to="/" className="flex items-center gap-2 group shrink-0">
            <m.span whileHover={{ rotate: 12 }} transition={{ type: 'spring', stiffness: 300 }} className="text-accent">
              <Dices size={22} />
            </m.span>
            <span className="font-display font-semibold text-accent group-hover:text-yellow-300 transition-colors">
              Auto-DM
            </span>
          </Link>

          <div className="flex items-center gap-1 overflow-x-auto scrollbar-none">
            {links.map((l) => {
              const active = isActive(loc.pathname, l.to, l.exact);
              return (
                <Link
                  key={l.to}
                  to={l.to}
                  className={`relative text-sm px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
                    active ? 'text-accent' : 'text-muted hover:text-gray-200'
                  }`}
                >
                  {active && (
                    <m.span
                      layoutId="nav-indicator"
                      className="absolute inset-0 bg-accent/10 border border-accent/20 rounded-lg"
                      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10">{l.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      <main
        className={`flex-1 w-full mx-auto px-4 min-h-0 ${
          isPlaySession
            ? 'py-2 max-w-[1600px] lg:overflow-hidden lg:flex lg:flex-col lg:flex-1'
            : 'py-6 md:py-8 max-w-7xl'
        }`}
      >
        <Outlet />
      </main>
    </div>
  );
}
