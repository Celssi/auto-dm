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
  createMode: 'manual' | 'ai';
  generating: boolean;
  newAdventureOpen: boolean;
  bootstrapping: boolean;
  form: { name: string; story_arc: string };
  generateForm: {
    character_id: string;
    mode: 'freeform' | 'module';
    theme: string;
    campaign_name: string;
    adventure_count: number;
    include_faerun: boolean;
    bootstrap_first: boolean;
  };
  adventureForm: {
    character_id: string;
    mode: 'freeform' | 'module';
    theme: string;
    adventure_name: string;
    include_faerun: boolean;
    auto_continue: boolean;
  };
}

export type CampaignsAction =
  | { type: 'set'; patch: Partial<CampaignsState> }
  | { type: 'patchForm'; patch: Partial<CampaignsState['form']> }
  | { type: 'patchGenerateForm'; patch: Partial<CampaignsState['generateForm']> }
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
  createMode: 'ai',
  generating: false,
  newAdventureOpen: false,
  bootstrapping: false,
  form: { name: '', story_arc: '' },
  generateForm: {
    character_id: '',
    mode: 'freeform',
    theme: '',
    campaign_name: '',
    adventure_count: 3,
    include_faerun: false,
    bootstrap_first: false,
  },
  adventureForm: {
    character_id: '',
    mode: 'freeform',
    theme: '',
    adventure_name: '',
    include_faerun: false,
    auto_continue: false,
  },
};

export function campaignsReducer(state: CampaignsState, action: CampaignsAction): CampaignsState {
  switch (action.type) {
    case 'set':
      return { ...state, ...action.patch };
    case 'patchForm':
      return { ...state, form: { ...state.form, ...action.patch } };
    case 'patchGenerateForm':
      return { ...state, generateForm: { ...state.generateForm, ...action.patch } };
    case 'patchAdventureForm':
      return { ...state, adventureForm: { ...state.adventureForm, ...action.patch } };
    default:
      return state;
  }
}
