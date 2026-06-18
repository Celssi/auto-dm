export const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const;

export const SKILLS: { id: string; ability: string; label: string }[] = [
  { id: 'acrobatics', ability: 'dex', label: 'Acrobatics' },
  { id: 'animal_handling', ability: 'wis', label: 'Animal Handling' },
  { id: 'arcana', ability: 'int', label: 'Arcana' },
  { id: 'athletics', ability: 'str', label: 'Athletics' },
  { id: 'deception', ability: 'cha', label: 'Deception' },
  { id: 'history', ability: 'int', label: 'History' },
  { id: 'insight', ability: 'wis', label: 'Insight' },
  { id: 'intimidation', ability: 'cha', label: 'Intimidation' },
  { id: 'investigation', ability: 'int', label: 'Investigation' },
  { id: 'medicine', ability: 'wis', label: 'Medicine' },
  { id: 'nature', ability: 'int', label: 'Nature' },
  { id: 'perception', ability: 'wis', label: 'Perception' },
  { id: 'performance', ability: 'cha', label: 'Performance' },
  { id: 'persuasion', ability: 'cha', label: 'Persuasion' },
  { id: 'religion', ability: 'int', label: 'Religion' },
  { id: 'sleight_of_hand', ability: 'dex', label: 'Sleight of Hand' },
  { id: 'stealth', ability: 'dex', label: 'Stealth' },
  { id: 'survival', ability: 'wis', label: 'Survival' },
];
