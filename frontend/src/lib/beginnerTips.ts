/** Short in-app explanations for beginners. Concept-level 2024 rules, not book text. */

export interface BeginnerTip {
  title: string;
  summary: string;
  kind?: string;
}

export const BEGINNER_TIPS: Record<string, BeginnerTip> = {
  'armor-class': {
    title: 'Armor Class',
    kind: 'rules',
    summary:
      'How hard you are to hit. Attack rolls must meet or beat this number. Typical formula: armor + Dexterity (light armor adds all DEX; medium caps DEX at +2; heavy adds no DEX) + shield (+2) + Defense fighting style (+1 while armored).',
  },
  initiative: {
    title: 'Initiative',
    kind: 'rules',
    summary:
      'Who acts first in combat. Roll 1d20 + Dexterity modifier. The Alert origin feat also adds your proficiency bonus. Higher total goes earlier.',
  },
  speed: {
    title: 'Speed',
    kind: 'rules',
    summary:
      'How far you can walk on your turn, in feet. A normal Human walk speed is 30 feet. Exhaustion reduces Speed by 5 feet per level.',
  },
  'hit-points': {
    title: 'Hit Points',
    kind: 'rules',
    summary:
      'Your remaining health. At 0 HP you fall unconscious and start death saving throws. Healing restores HP up to your maximum.',
  },
  'hit-dice': {
    title: 'Hit Dice',
    kind: 'rules',
    summary:
      'Used during a Short Rest to recover HP: roll the die, add Constitution modifier (minimum 1 HP). You regain spent Hit Dice on a Long Rest. Fighters use d10.',
  },
  'heroic-inspiration': {
    title: 'Heroic Inspiration',
    kind: 'rules',
    summary:
      '2024 Heroic Inspiration: spend it to reroll one die (d20, damage, and similar). Humans with Resourceful gain it when they finish a Long Rest.',
  },
  'death-saves': {
    title: 'Death Saving Throws',
    kind: 'rules',
    summary:
      'While at 0 HP, roll 1d20 at the start of your turn. 10 or higher is a success, 9 or lower is a failure. Three successes: you stabilize. Three failures: you die. A 1 counts as two failures. A 20 restores 1 HP and you wake.',
  },
  'proficiency-bonus': {
    title: 'Proficiency Bonus',
    kind: 'rules',
    summary:
      'Added to rolls you are trained in: attacks with proficient weapons, proficient skills and saves, and spell attacks. It is +2 at levels 1-4, then rises every four levels.',
  },
  'ability-scores': {
    title: 'Ability Scores',
    kind: 'rules',
    summary:
      'Six numbers that describe your character. Each score has a modifier: (score - 10) ÷ 2, rounded down. Example: 16 is +3, 8 is -1. You add the modifier to related rolls.',
  },
  'saving-throws': {
    title: 'Saving Throws',
    kind: 'rules',
    summary:
      'Rolls to resist danger. 1d20 + ability modifier, plus proficiency if you are trained in that save. Fighters are proficient in Strength and Constitution.',
  },
  skills: {
    title: 'Skills',
    kind: 'rules',
    summary:
      'Trained ways to use abilities (Athletics uses Strength, Stealth uses Dexterity, and so on). A filled dot means you add your proficiency bonus. Filled skills are the ones you chose at creation.',
  },
  'passive-perception': {
    title: 'Passive Perception',
    kind: 'rules',
    summary:
      'Your noticing score when you are not actively searching: 10 + Wisdom modifier + proficiency if you are trained in Perception. The DM uses this for hidden creatures and clues.',
  },
  'second-wind': {
    title: 'Second Wind',
    kind: 'feature',
    summary:
      'Fighter Bonus Action: regain 1d10 + your Fighter level HP. Two uses at level 1 (more later). Regain 1 use on a Short Rest, all uses on a Long Rest.',
  },
  'weapon-mastery': {
    title: 'Weapon Mastery',
    kind: 'feature',
    summary:
      '2024 rule: if you have mastery with a weapon, you can use its extra property (Graze, Sap, Slow, and others) when you attack with that weapon. Fighters pick several weapons and may change one after a Long Rest.',
  },
  graze: {
    title: 'Graze',
    kind: 'feature',
    summary:
      'Greatsword mastery. If your attack roll misses, you still deal damage equal to the ability modifier used for the attack.',
  },
  sap: {
    title: 'Sap',
    kind: 'feature',
    summary:
      'Longsword and spear mastery. On a hit, the target has Disadvantage on its next attack roll before the start of your next turn.',
  },
  slow: {
    title: 'Slow',
    kind: 'feature',
    summary: 'On a hit, you can reduce the target Speed by 10 feet until the start of your next turn.',
  },
  nick: {
    title: 'Nick',
    kind: 'feature',
    summary:
      'When you make the extra attack from the Light property, you can make it as part of the Attack action instead of using a Bonus Action.',
  },
  vex: {
    title: 'Vex',
    kind: 'feature',
    summary:
      'On a hit, you have Advantage on your next attack roll against that target before the end of your next turn.',
  },
  cleave: {
    title: 'Cleave',
    kind: 'feature',
    summary:
      'Melee hit: make one extra attack against a second creature within 5 feet of the first and within your reach. Do not add your ability modifier to that damage unless it is negative. Once per turn.',
  },
  push: {
    title: 'Push',
    kind: 'feature',
    summary: 'On a hit, you can push a Large or smaller target up to 10 feet straight away from you. No saving throw.',
  },
  topple: {
    title: 'Topple',
    kind: 'feature',
    summary:
      'On a hit, the target makes a Constitution save (DC 8 + the attack ability modifier + your Proficiency Bonus) or has the Prone condition.',
  },
  feats: {
    title: 'Feats',
    kind: 'rules',
    summary:
      'Special trained abilities. In 2024, your background gives an Origin feat, and Humans (Versatile) pick a second Origin feat. Fighting Style is also a feat for Fighters.',
  },
  conditions: {
    title: 'Conditions',
    kind: 'rules',
    summary:
      'Temporary states such as Poisoned, Prone, or Frightened. Each one changes what you can do. Tap or focus a condition name for a short reminder.',
  },
  exhaustion: {
    title: 'Exhaustion',
    kind: 'rules',
    summary:
      'Each level of Exhaustion subtracts 2 from d20 tests (attacks, checks, saves) and reduces Speed by 5 feet. Six levels is death. A Long Rest removes one level.',
  },
  spellcasting: {
    title: 'Spellcasting',
    kind: 'rules',
    summary:
      'Save DC is 8 + proficiency + your spellcasting ability modifier. Spell attack is proficiency + that modifier. On a turn you expend only one spell slot to cast a spell. Cantrips do not use slots.',
  },
  'spell-slots': {
    title: 'Spell Slots',
    kind: 'rules',
    summary:
      'Fuel for leveled spells. Casting a 1st-level spell spends a 1st-level slot (or a higher one if you upcast). Cantrips are free. Slots return on a Long Rest (Warlock Pact slots also return on a Short Rest).',
  },
  concentration: {
    title: 'Concentration',
    kind: 'rules',
    summary:
      'Some spells last only while you concentrate. You can concentrate on one such spell at a time. Taking damage may force a Constitution save to keep it.',
  },
  oracle: {
    title: 'Oracle',
    kind: 'rules',
    summary:
      'A solo-play yes/no helper. The app rolls a d6 so the answer is not invented: 1-3 no, 4-6 yes, with optional twists. Use it when you need an impartial ruling.',
  },
  'bt-health': {
    title: 'Health',
    kind: 'rules',
    summary: 'Brambletrek: physical well-being, maximum 20. Reaching 0 is a crisis for the journey.',
  },
  'bt-morale': {
    title: 'Morale',
    kind: 'rules',
    summary: 'Brambletrek: spirit and nerve, maximum 20. Low morale makes the road feel heavier.',
  },
  'bt-supplies': {
    title: 'Supplies',
    kind: 'rules',
    summary: 'Brambletrek: food, gear, and provisions, maximum 20. Spend them when events call for upkeep.',
  },
  'bt-cards': {
    title: 'Journey cards',
    kind: 'rules',
    summary:
      'Brambletrek uses a 52-card deck. Draw 4 cards per day. Red (hearts, diamonds) is favourable. Black (clubs, spades) is unfortunate. Never invent a card the tools did not draw.',
  },
  'bt-legacy': {
    title: 'Legacy',
    kind: 'rules',
    summary:
      'Your Gnawborn calling among six Legacies. It changes starting resources and special abilities. Pick the one that matches how you want to travel.',
  },
  'bt-overcome': {
    title: 'Overcome the Odds',
    kind: 'rules',
    summary:
      'A Brambletrek push when a check or event goes badly. Spend the listed cost (often a resource or a consequence) to try again. Follow the card and rules text, not improvisation.',
  },
  'bt-combat': {
    title: 'Brambletrek combat',
    kind: 'rules',
    summary:
      'Combat uses Initiative plus a Tactic card from your hand. Play a tactic, resolve the listed effect, then continue the turn loop until Health hits 0 or the foe is defeated.',
  },
  'bt-tactics': {
    title: 'Tactic cards',
    kind: 'rules',
    summary:
      'Your combat hand. Each tactic is a specific move (damage, guard, recover). Play one on your turn; do not invent extra effects.',
  },
  lonelog: {
    title: 'Lonelog',
    kind: 'rules',
    summary: 'A running list of rolls, rests, oracles, and other mechanics. It is not the story text.',
  },
  audit: {
    title: 'Audit',
    kind: 'rules',
    summary: 'A detailed record of HP, slots, and other tracked changes so you can see what the app applied.',
  },
  gnawborn: {
    title: 'Gnawborn',
    kind: 'rules',
    summary: 'A Brambletrek player character: a small forest folk on a card-driven solo journey.',
  },
  currency: {
    title: 'Currency',
    kind: 'rules',
    summary: 'Coins on the sheet: cp copper, sp silver, ep electrum, gp gold, pp platinum. 10 cp = 1 sp, 10 sp = 1 gp.',
  },
  equipment: {
    title: 'Equipment',
    kind: 'rules',
    summary: 'What you carry. Worn armor and weapons appear here even when they are also listed in Combat or Features.',
  },
  armor: {
    title: 'Armor',
    kind: 'rules',
    summary:
      'Worn armor sets your Armor Class. Light adds all Dexterity; medium adds DEX up to +2; heavy adds none. A shield adds +2.',
  },
};

export function beginnerTip(id: string): BeginnerTip | null {
  return BEGINNER_TIPS[id] || BEGINNER_TIPS[id.toLowerCase().replace(/[^a-z0-9]+/g, '-')] || null;
}
