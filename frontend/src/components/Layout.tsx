import { lazy, Suspense } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Library, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useBookReader } from '../context/BookReaderContext';
import { m } from '../lib/framer';
import GameSwitcher from './GameSwitcher';
import BottomNav from './BottomNav';

const PdfReaderOverlay = lazy(() => import('./books/PdfReaderOverlay'));

const links = [
  { to: '/', label: 'Home', exact: true },
  { to: '/characters', label: 'Characters' },
  { to: '/campaigns', label: 'Campaigns' },
  { to: '/adventures', label: 'Adventures' },
  { to: '/play', label: 'Play' },
  { to: '/books', label: 'Books' },
  { to: '/settings', label: 'Settings' },
];

function isActive(pathname: string, to: string, exact?: boolean) {
  if (exact) return pathname === to;
  return pathname.startsWith(to);
}

export default function Layout() {
  const loc = useLocation();
  const { signOut } = useAuth();
  const { open, openReader } = useBookReader();
  const isPlaySession = /^\/play\/[^/]+/.test(loc.pathname);

  return (
    <div className={`flex flex-col ${isPlaySession ? 'h-dvh overflow-hidden' : 'min-h-screen'}`}>
      <nav className="border-b border-border/80 bg-panel/70 backdrop-blur-md shrink-0 z-20">
        <div
          className={`mx-auto px-3 sm:px-4 py-2.5 flex items-center gap-2 sm:gap-3 md:gap-6 min-w-0 ${
            isPlaySession ? 'max-w-[1600px]' : 'max-w-7xl'
          }`}
        >
          <Link to="/" className="flex items-center gap-2 group shrink-0 min-h-11" aria-label="Auto-DM home">
            <m.span whileHover={{ rotate: 12 }} transition={{ type: 'spring', stiffness: 300 }} className="inline-flex">
              <img src="/icon.svg" alt="" width={28} height={28} className="h-7 w-7 rounded-md" />
            </m.span>
            <span className="hidden min-[400px]:inline font-display font-semibold text-accent group-hover:opacity-80 transition-opacity">
              Auto-DM
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1 overflow-x-auto scrollbar-none">
            {links.map((l) => {
              const active = isActive(loc.pathname, l.to, l.exact);
              return (
                <Link
                  key={l.to}
                  to={l.to}
                  className={`relative text-sm min-h-11 px-3 inline-flex items-center rounded-xl whitespace-nowrap transition-colors ${
                    active ? 'text-accent' : 'text-muted hover:text-gray-200'
                  }`}
                >
                  {active && (
                    <m.span
                      layoutId="nav-indicator"
                      className="absolute inset-0 bg-accent/10 border border-accent/20 rounded-xl"
                      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10">{l.label}</span>
                </Link>
              );
            })}
          </div>

          <div className="ml-auto flex items-center gap-1.5 sm:gap-2 min-w-0">
            <button
              type="button"
              className="btn-ghost min-h-11 min-w-11 px-3 shrink-0 inline-flex items-center justify-center gap-1.5"
              onClick={openReader}
              aria-label="Open rulebook"
            >
              <Library size={16} aria-hidden="true" />
              <span className="hidden sm:inline">Open rulebook</span>
            </button>
            <GameSwitcher />
            <button
              type="button"
              className="btn-ghost min-h-11 min-w-11 px-3 shrink-0 inline-flex items-center justify-center gap-1.5"
              onClick={() => void signOut()}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut size={14} aria-hidden="true" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </nav>

      <main
        className={`flex-1 w-full mx-auto px-4 min-h-0 ${
          isPlaySession
            ? 'py-2 max-w-[1600px] overflow-hidden flex flex-col flex-1'
            : 'py-6 md:py-8 max-w-7xl pb-24 md:pb-8'
        }`}
      >
        <Outlet key={loc.pathname} />
      </main>

      {!isPlaySession && <BottomNav />}
      {open && (
        <Suspense
          fallback={
            <div className="fixed inset-0 z-40 bg-bg flex items-center justify-center text-sm text-muted">
              Opening reader…
            </div>
          }
        >
          <PdfReaderOverlay />
        </Suspense>
      )}
    </div>
  );
}
