import type { AdventureMeta, CampaignFull, JournalEntry } from '../../api/client';

export type CampaignTab = 'story' | 'adventures' | 'npcs' | 'locations';

export interface CampaignsState {
  campaigns: { id: string; name: string }[];
  campaignsLoaded: boolean;
  selected: CampaignFull | null;
  campaignAdventures: AdventureMeta[];
  adventuresLoaded: boolean;
  characters: { id: string; name: string }[];
  tab: CampaignTab;
  entry: JournalEntry | null;
  error: string | null;
  creating: boolean;
  newAdventureOpen: boolean;
  bootstrapping: boolean;
  form: { name: string; story_arc: string };
  adventureForm: {
    character_id: string;
    mode: 'freeform' | 'module';
    theme: string;
    adventure_name: string;
    include_faerun: boolean;
  };
}

export type CampaignsAction =
  | { type: 'set'; patch: Partial<CampaignsState> }
  | { type: 'patchForm'; patch: Partial<CampaignsState['form']> }
  | { type: 'patchAdventureForm'; patch: Partial<CampaignsState['adventureForm']> };

export const initialCampaignsState: CampaignsState = {
  campaigns: [],
  campaignsLoaded: false,
  selected: null,
  campaignAdventures: [],
  adventuresLoaded: false,
  characters: [],
  tab: 'story',
  entry: null,
  error: null,
  creating: false,
  newAdventureOpen: false,
  bootstrapping: false,
  form: { name: '', story_arc: '' },
  adventureForm: {
    character_id: '',
    mode: 'freeform',
    theme: '',
    adventure_name: '',
    include_faerun: false,
  },
};

export function campaignsReducer(state: CampaignsState, action: CampaignsAction): CampaignsState {
  switch (action.type) {
    case 'set':
      return { ...state, ...action.patch };
    case 'patchForm':
      return { ...state, form: { ...state.form, ...action.patch } };
    case 'patchAdventureForm':
      return { ...state, adventureForm: { ...state.adventureForm, ...action.patch } };
    default:
      return state;
  }
}
