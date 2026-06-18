export const WIZARD_STEPS = ['Basics', 'Origin', 'Abilities', 'Skills & spells', 'Review'] as const;
export const WIZARD_ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const;

export interface WizardOption {
  id: string;
  label: string;
  [key: string]: unknown;
}

export interface WizardClassOption extends WizardOption {
  hit_die?: number;
  spellcasting?: string | null;
  spell_list?: string;
  skill_choices?: number;
  skill_options?: string[] | 'any';
  cantrips_by_level?: number[];
  prepared_by_level?: number[];
  spells_known_by_level?: number[];
}

export const defaultWizardCharacter = {
  name: '',
  species: '',
  class_name: '',
  subclass: '',
  background: '',
  alignment: '',
  level: 1,
  xp: 0,
  hp: 0,
  max_hp: 0,
  ac: 10,
  speed: 30,
  hit_die: 8,
  ability_scores: { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 },
  base_ability_scores: {},
  ability_scores_set: false,
  skill_proficiencies: [],
  class_skill_choices: [],
  save_proficiencies: [],
  cantrips: [],
  prepared_spells: [],
  known_spells: [],
  spell_slots: {},
  weapons: [],
  inventory: [],
  currency: {},
  feats: [],
  origin_feat: '',
  campaign_setting: 'freeform',
  campaign_notes: '',
  human_skill: '',
};
