import type { AdventureFull } from '../../api/client';

export interface AdventuresState {
  adventures: { id: string; name: string; mode: string }[];
  adventuresLoaded: boolean;
  characters: { id: string; name: string }[];
  campaigns: { id: string; name: string }[];
  selected: AdventureFull | null;
  creating: boolean;
  form: {
    name: string;
    mode: string;
    theme: string;
    character_id: string;
    campaign_id: string;
    include_faerun: boolean;
  };
  error: string | null;
}

export type AdventuresAction =
  | { type: 'set'; patch: Partial<AdventuresState> }
  | { type: 'patchForm'; patch: Partial<AdventuresState['form']> };

export const initialAdventuresState: AdventuresState = {
  adventures: [],
  adventuresLoaded: false,
  characters: [],
  campaigns: [],
  selected: null,
  creating: false,
  form: {
    name: '',
    mode: 'freeform',
    theme: '',
    character_id: '',
    campaign_id: '',
    include_faerun: false,
  },
  error: null,
};

export function adventuresReducer(state: AdventuresState, action: AdventuresAction): AdventuresState {
  switch (action.type) {
    case 'set':
      return { ...state, ...action.patch };
    case 'patchForm':
      return { ...state, form: { ...state.form, ...action.patch } };
    default:
      return state;
  }
}
