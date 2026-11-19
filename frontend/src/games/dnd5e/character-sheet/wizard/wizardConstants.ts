export const WIZARD_STEPS = [
  'Basics',
  'Origin',
  'Abilities',
  'Skills & spells',
  'Features & traits',
  'Starting gear',
  'Review',
] as const;
export const WIZARD_ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const;

/** Short beginner blurbs for class chips. Not PHB text. */
export const CLASS_BLURBS: Record<string, string> = {
  barbarian: 'Hits hard, shrugs off damage. Hit Die d12.',
  bard: 'Spells, skills, and support. Hit Die d8.',
  cleric: 'Divine spells and support. Hit Die d8.',
  druid: 'Nature spells and Wild Shape. Hit Die d8.',
  fighter: 'Weapons, armor, Second Wind. Hit Die d10.',
  monk: 'Unarmed strikes and mobility. Hit Die d8.',
  paladin: 'Smite, spells, and heavy armor. Hit Die d10.',
  ranger: 'Skirmisher with nature spells. Hit Die d10.',
  rogue: 'Sneak Attack and skills. Hit Die d8.',
  sorcerer: 'Innate spellcasting. Hit Die d6.',
  warlock: 'Pact spells that return on a Short Rest. Hit Die d8.',
  wizard: 'Learns and prepares many spells. Hit Die d6.',
};

export const BACKGROUND_BLURBS: Record<string, string> = {
  acolyte: 'Temple life. Origin feat: Magic Initiate (Cleric).',
  criminal: 'Streets and shadows. Origin feat: Alert.',
  sage: 'Study and lore. Origin feat: Magic Initiate (Wizard).',
  soldier: 'Rank and file. Origin feat: Savage Attacker.',
  artisan: 'Craft and trade. Origin feat: Crafter.',
  charlatan: 'Tricks and cons. Origin feat: Skilled.',
  entertainer: 'Stage and crowd. Origin feat: Musician.',
  farmer: 'Fields and livestock. Origin feat: Tough.',
  guide: 'Trails and weather. Origin feat: Magic Initiate (Druid).',
  hermit: 'Seclusion. Origin feat: Healer.',
  merchant: 'Deals and travel. Origin feat: Lucky.',
  noble: 'Status and influence. Origin feat: Skilled.',
  sailor: 'Ships and ports. Origin feat: Tavern Brawler.',
  scribe: 'Records and ink. Origin feat: Skilled.',
  wayfarer: 'Roads and camps. Origin feat: Lucky.',
  guard: 'Watch and patrol. Origin feat: Alert.',
};

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
  appearance: '',
  human_skill: '',
  feature_choices: {},
  fighting_style_feat: '',
  weapon_mastery: [],
  versatile_origin_feat: '',
  background_gear_choice: '',
  starting_gear_choice: '',
};
