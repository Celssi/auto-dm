import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { useGame } from '../context/GameContext';
import { GAMES } from '../games/registry';
import { leaveScopedRoute } from '../lib/gameScope';

export default function GameSwitcher() {
  const { gameId, game, setGameId } = useGame();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [open]);

  const selectGame = (id: string) => {
    setOpen(false);
    if (id === gameId) return;
    setGameId(id);
    const next = leaveScopedRoute(location.pathname);
    if (next) navigate(next);
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className="btn-ghost min-h-11 inline-flex items-center gap-1.5 max-w-[12rem] sm:max-w-none"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="truncate">{game.label}</span>
        <ChevronDown size={14} className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <ul
          role="listbox"
          className="absolute right-0 mt-1 z-30 min-w-[14rem] rounded-2xl border border-border bg-panel p-1 shadow-panel"
        >
          {GAMES.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                role="option"
                aria-selected={item.id === gameId}
                className={`w-full text-left min-h-11 px-3 rounded-lg text-sm transition-colors ${
                  item.id === gameId ? 'bg-accent/15 text-accent' : 'text-gray-200 hover:bg-panel-hover'
                }`}
                onClick={() => selectGame(item.id)}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
