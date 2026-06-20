export interface ClassLevel {
  class_name: string;
  level: number;
  subclass?: string;
  class_skill_choices?: string[];
}

export interface Character {
  id?: string;
  name: string;
  species: string;
  class_name: string;
  subclass: string;
  background: string;
  alignment: string;
  level: number;
  xp: number;
  hp: number;
  max_hp: number;
  ac: number;
  speed: number;
  hit_die: number;
  ability_scores: Record<string, number>;
  skill_proficiencies: string[];
  save_proficiencies: string[];
  cantrips: string[];
  prepared_spells: string[];
  known_spells: string[];
  spell_slots: Record<string, number>;
  weapons: Array<{ name: string; damage: string; damage_type: string; ability: string }>;
  inventory: string[];
  currency: Record<string, number>;
  feats: string[];
  origin_feat: string;
  heroic_inspiration?: boolean;
  hit_dice_max?: number;
  hit_dice_spent?: number;
  death_save_successes?: number;
  death_save_failures?: number;
  languages?: string[];
  tool_proficiencies?: string[];
  attuned_items?: string[];
  appearance?: string;
  equipment_notes?: string;
  wild_shape_uses?: number;
  concentration?: string;
  conditions?: string[];
  size?: string;
  asi_choices?: Record<string, unknown>[];
  class_skill_choices?: string[];
  classes?: ClassLevel[];
  campaign_setting: string;
  campaign_notes: string;
  [key: string]: unknown;
}

export interface Adventure {
  id: string;
  name: string;
  mode: string;
  theme?: string;
  outline?: string;
  log?: string;
  include_faerun?: boolean;
  status?: string;
}

export interface Session {
  id: string;
  name: string;
  character_id: string;
  adventure_id: string;
  include_faerun?: boolean;
  messages?: Array<{ role: string; content: string }>;
  lonelog?: string;
}

export interface Source {
  source_label?: string;
  page?: string;
  text?: string;
}

export interface PickBudget {
  limit_before: number;
  limit_after: number;
  current: number;
  limit_increased: boolean;
  additional_picks: number;
}

export interface LevelUpPreview {
  can_level: boolean;
  reason?: string;
  target_class?: string;
  target_class_label?: string;
  class_level_before?: number;
  class_level_after?: number;
  total_level_after?: number;
  hit_die?: number;
  proficiency_bonus_increases?: boolean;
  proficiency_bonus_after?: number;
  cantrips?: PickBudget;
  class_cantrips?: PickBudget;
  spells?: PickBudget & { field: string; label: string };
  spell_list?: { cantrips: string[]; options: string[] };
  asi_this_level?: boolean;
  needs_subclass?: boolean;
  notices?: string[];
}
