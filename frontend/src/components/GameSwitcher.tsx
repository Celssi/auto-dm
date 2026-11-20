import { useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { useGame } from '../context/GameContext';
import { GAMES } from '../games/registry';
import { leaveScopedRoute } from '../lib/gameScope';
import AnchoredPopover from './ui/AnchoredPopover';

export default function GameSwitcher() {
  const { gameId, game, setGameId } = useGame();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const selectGame = (id: string) => {
    setOpen(false);
    if (id === gameId) return;
    setGameId(id);
    const next = leaveScopedRoute(location.pathname);
    if (next) navigate(next);
  };

  return (
    <div className="relative min-w-0">
      <button
        ref={triggerRef}
        type="button"
        className="btn-ghost min-h-11 inline-flex items-center gap-1.5 max-w-full min-w-0 px-3"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Current game ${game.label}. Switch game.`}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="truncate">{game.label}</span>
        <ChevronDown size={14} className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      <AnchoredPopover
        open={open}
        triggerRef={triggerRef}
        onClose={() => setOpen(false)}
        role="listbox"
        className="sheet-menu min-w-[14rem] rounded-2xl"
      >
        {GAMES.map((item) => (
          <button
            key={item.id}
            type="button"
            role="option"
            aria-selected={item.id === gameId}
            className={`sheet-menu-item ${item.id === gameId ? 'bg-panel-hover text-accent' : ''}`}
            onClick={() => selectGame(item.id)}
          >
            {item.label}
          </button>
        ))}
      </AnchoredPopover>
    </div>
  );
}
