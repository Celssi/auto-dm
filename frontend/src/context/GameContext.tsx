import { createContext, use, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { DEFAULT_GAME_ID, GAMES, getGame, isGameId, type GameDefinition, type GameId } from '../games/registry';

const STORAGE_KEY = 'auto-dm:game-id';

interface GameContextType {
  gameId: GameId;
  game: GameDefinition;
  setGameId: (next: string) => void;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

function readStoredGameId(): GameId {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) ?? undefined;
    if (isGameId(stored)) return stored;
  } catch {
    /* ignore quota / private mode */
  }
  return DEFAULT_GAME_ID;
}

export function GameProvider({ children }: { children: ReactNode }) {
  const [gameId, setGameIdState] = useState<GameId>(readStoredGameId);
  const game = getGame(gameId);

  const setGameId = useCallback((next: string) => {
    const resolved = isGameId(next) ? next : DEFAULT_GAME_ID;
    setGameIdState(resolved);
    try {
      localStorage.setItem(STORAGE_KEY, resolved);
    } catch {
      /* ignore quota / private mode */
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.game = gameId;
  }, [gameId]);

  const value = useMemo(() => ({ gameId, game, setGameId }), [gameId, game, setGameId]);

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
}

export function useGame() {
  const context = use(GameContext);
  if (context === undefined) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
}

export { GAMES };
