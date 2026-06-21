import type { Character } from '../../../types';
import type { PdfModule } from './characterSheetPdfTypes';
import { abilityMod, formatMod, saveBonus, skillBonus } from './sheetUtils';
import { ABILITY_NAMES, SKILLS_BY_ABILITY, pdfStyles as s } from './characterSheetPdfStyles';
import { createPdfShapes } from './characterSheetPdfShapes';

export function createAbilityBlock(pdf: PdfModule) {
  const { Text, View } = pdf;
  const { CirclePip } = createPdfShapes(pdf);

  return function AbilityBlock({
    ab,
    c,
    profs,
    saves,
  }: {
    ab: string;
    c: Character;
    profs: Set<string>;
    saves: Set<string>;
  }) {
    const scores = c.ability_scores || {};
    const score = scores[ab] ?? 10;
    const skills = SKILLS_BY_ABILITY[ab] || [];

    return (
      <View style={[s.box, { marginBottom: 2, paddingHorizontal: 2, paddingBottom: 2 }]}>
        <Text style={[s.label, { textAlign: 'center', marginTop: 1 }]}>{ABILITY_NAMES[ab]}</Text>
        <View style={[s.center, s.modCircle, { alignSelf: 'center' }]}>
          <Text style={s.modText}>{formatMod(abilityMod(score))}</Text>
        </View>
        <View style={[s.scoreBox, { alignSelf: 'center' }]}>
          <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold' }}>{score}</Text>
        </View>
        <View style={s.skillRow}>
          <CirclePip filled={saves.has(ab)} />
          <Text style={s.skillText}>Saving Throw</Text>
          <Text style={s.skillMod}>{saveBonus(c, ab)}</Text>
        </View>
        {skills.map((sk) => (
          <View key={sk.id} style={s.skillRow}>
            <CirclePip filled={profs.has(sk.id)} />
            <Text style={s.skillText}>{sk.label}</Text>
            <Text style={s.skillMod}>{skillBonus(c, sk.id, sk.ability)}</Text>
          </View>
        ))}
      </View>
    );
  };
}
