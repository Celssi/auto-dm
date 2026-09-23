export interface ClassLevel {
  class_name: string;
  level: number;
  subclass?: string;
  class_skill_choices?: string[];
}

export interface Character {
  id?: string;
  game_id?: string;
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
  base_ability_scores?: Record<string, number>;
  ability_scores_set?: boolean;
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
  luck_points_remaining?: number;
  savage_attacker_used_this_turn?: boolean;
  concentration?: string;
  conditions?: string[];
  size?: string;
  asi_choices?: Record<string, unknown>[];
  class_skill_choices?: string[];
  feature_choices?: Record<string, unknown>;
  fighting_style_feat?: string;
  weapon_mastery?: string[];
  versatile_origin_feat?: string;
  background_gear_choice?: string;
  starting_gear_choice?: string;
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
  pending_choices?: Array<Record<string, unknown>>;
  missing_choices?: string[];
}

export interface BrambletrekCharacter {
  id?: string;
  game_id?: string;
  name: string;
  reason_band: string;
  background_band: string;
  trinket_band: string;
  legacy: string;
  health: number;
  morale: number;
  supplies: number;
  journey_day: number;
  in_aldwund: boolean;
  active_adventure: string;
  reason_card?: string;
  background_card?: string;
  trinket_card?: string;
  notes?: string;
  legacy_abilities_used?: Record<string, boolean>;
  resource_cards?: Record<string, string[]>;
  resource_base_health?: number | null;
  resource_base_morale?: number | null;
  resource_base_supplies?: number | null;
  oracle_relic?: boolean;
  [key: string]: unknown;
}

export interface BrambletrekCombatState {
  status: string;
  mode?: string;
  opponent?: { id?: string; label?: string; hp?: number; max_hp?: number };
  player?: { hp?: number };
  initiative?: { player_card?: string; opponent_card?: string; first?: string };
  tactic_hand?: string[];
  turn?: string;
  finale_phase?: string;
  phase_progress?: Record<string, unknown>;
  phase_goals?: { damage_goal?: number; rounds_goal?: number; bands_goal?: number };
  phase_complete?: boolean;
  can_advance_phase?: boolean;
  log?: string[];
  combat_preview?: string;
  item_used_this_phase?: boolean;
  can_search_item?: boolean;
  combat_items?: string[];
  buffs?: Record<string, unknown>;
}

export interface JourneyEvent {
  index: number;
  card: string;
  zone: string;
  applied: boolean;
  can_apply: boolean;
  label?: string;
  preview: string;
  needs_item: boolean;
  item_card?: string | null;
  item_label?: string | null;
  item_preview?: string | null;
  combat?: boolean;
  combat_preview?: string;
}

export interface PendingJourney {
  events: JourneyEvent[];
  shortcut_id?: string;
  exploration_table?: string;
}

export interface DragonkeepGemOption {
  id: string;
  label: string;
  short: string;
  completed: boolean;
}

export interface DragonkeepState {
  phase: string;
  phase_label: string;
  path_step: number;
  path_total: number;
  location_title: string;
  location_body: string;
  needs_path_draw: boolean;
  path_resolved: boolean;
  pending_path_card: string;
  pending_path_preview: string;
  pending_path_label: string;
  active_gem: string;
  active_gem_label: string;
  gems: DragonkeepGemOption[];
  gems_completed: string[];
  met_eolan: boolean;
  door_opened: boolean;
  combat_context?: Record<string, unknown> | null;
  combat_preview?: string;
  finale_step?: string;
  finale_step_label?: string;
  finale_phase?: string;
  eolan_wounded?: boolean;
  instructions: string;
  actions: string[];
  module_label: string;
}

export interface LegacyAbility {
  id: string;
  label: string;
  description: string;
  tags: string[];
  used: boolean;
}

export interface BrambletrekCharacterHeader {
  name: string;
  health: number;
  morale: number;
  supplies: number;
  journey_day: number;
  legacy: string;
  legacy_label?: string;
  in_aldwund?: boolean;
  active_adventure?: string;
}
