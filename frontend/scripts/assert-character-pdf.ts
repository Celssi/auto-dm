import type { Character } from '../src/types';
import {
  characterPdfFilename,
  renderCharacterPdfBlob,
} from '../src/games/dnd5e/character-sheet/characterSheetPdfDownload';

function sampleFighter(): Character {
  return {
    name: 'Sample Fighter',
    species: 'human',
    class_name: 'fighter',
    subclass: '',
    background: 'soldier',
    alignment: 'neutral',
    level: 1,
    xp: 0,
    hp: 12,
    max_hp: 12,
    ac: 16,
    speed: 30,
    hit_die: 10,
    ability_scores: { str: 16, dex: 14, con: 15, int: 8, wis: 12, cha: 10 },
    skill_proficiencies: ['athletics', 'intimidation'],
    save_proficiencies: ['str', 'con'],
    cantrips: [],
    prepared_spells: [],
    known_spells: [],
    spell_slots: {},
    weapons: [{ name: 'Longsword', damage: '1d8', damage_type: 'slashing', ability: 'str' }],
    inventory: ['Chain mail', 'Shield'],
    currency: { gp: 10, sp: 0, cp: 0, ep: 0, pp: 0 },
    feats: [],
    origin_feat: 'Savage Attacker',
    heroic_inspiration: true,
    campaign_setting: '',
    campaign_notes: '',
  };
}

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function main() {
  assert(
    characterPdfFilename('Larry Swordstein') === 'Larry Swordstein-sheet.pdf',
    'filename keeps the character name',
  );
  assert(!characterPdfFilename('A/B').includes('/'), 'filename strips path separators');
  const blob = await renderCharacterPdfBlob(sampleFighter(), {
    class_features: { fighter: ['Fighting Style', 'Second Wind'] },
  });
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const header = String.fromCharCode(...bytes.slice(0, 5));
  assert(header === '%PDF-', `expected a PDF header, got ${JSON.stringify(header)}`);
  assert(blob.size > 1000, `PDF too small: ${blob.size}`);
  console.log(`ok pdf ${blob.size} bytes ${characterPdfFilename('Sample Fighter')}`);
}

void main();
