import type { AdventureMeta, CampaignFull, CampaignMeta, JournalEntry } from '../../api/client';

export type CampaignTab = 'story' | 'adventures' | 'npcs' | 'locations';

export interface CampaignsState {
  campaigns: CampaignMeta[];
  campaignsLoaded: boolean;
  selected: CampaignFull | null;
  campaignAdventures: AdventureMeta[];
  allAdventures: AdventureMeta[];
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
  linkingCharacter: boolean;
  copyOpen: boolean;
  copyingCampaign: boolean;
  copyForm: { character_id: string; name: string };
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
  | { type: 'patchAdventureForm'; patch: Partial<CampaignsState['adventureForm']> }
  | { type: 'patchCopyForm'; patch: Partial<CampaignsState['copyForm']> };

export const initialCampaignsState: CampaignsState = {
  campaigns: [],
  campaignsLoaded: false,
  selected: null,
  campaignAdventures: [],
  allAdventures: [],
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
  linkingCharacter: false,
  copyOpen: false,
  copyingCampaign: false,
  copyForm: { character_id: '', name: '' },
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
    case 'patchCopyForm':
      return { ...state, copyForm: { ...state.copyForm, ...action.patch } };
    default:
      return state;
  }
}
