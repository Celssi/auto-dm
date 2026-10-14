import type { Character } from '../../types';
import type { CharacterRosterEntry } from '../../lib/displayText';

export type CharactersMode = 'list' | 'wizard' | 'view';

export interface CharactersState {
  roster: CharacterRosterEntry[];
  rosterLoaded: boolean;
  activeId: string | null;
  character: Character | null;
  summary: Record<string, unknown>;
  mode: CharactersMode;
  levelUpOpen: boolean;
  error: string | null;
}

export type CharactersAction = { type: 'set'; patch: Partial<CharactersState> };

export const initialCharactersState: CharactersState = {
  roster: [],
  rosterLoaded: false,
  activeId: null,
  character: null,
  summary: {},
  mode: 'list',
  levelUpOpen: false,
  error: null,
};

export function charactersReducer(state: CharactersState, action: CharactersAction): CharactersState {
  if (action.type === 'set') return { ...state, ...action.patch };
  return state;
}
