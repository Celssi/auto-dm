import type { Character } from '../../types';
import type { PdfModule } from './characterSheetPdfTypes';
import { abilityMod, formatMod, saveBonus, skillBonus } from './sheetUtils';
import { ABILITY_NAMES, SKILLS_BY_ABILITY, pdfStyles as s } from './characterSheetPdfStyles';

export function createAbilityBlock(pdf: PdfModule) {
  const { Text, View } = pdf;

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
      <View style={[s.box, { marginBottom: 3, paddingHorizontal: 3, paddingBottom: 3 }]}>
        <Text style={[s.label, { textAlign: 'center', marginTop: 2 }]}>{ABILITY_NAMES[ab]}</Text>
        <View style={[s.center, s.modCircle, { alignSelf: 'center' }]}>
          <Text style={s.modText}>{formatMod(abilityMod(score))}</Text>
        </View>
        <View style={[s.scoreBox, { alignSelf: 'center' }]}>
          <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold' }}>{score}</Text>
        </View>
        <View style={[s.row, { alignItems: 'center', marginTop: 3, paddingLeft: 2 }]}>
          <Text style={s.dot}>{saves.has(ab) ? '●' : '○'}</Text>
          <Text style={{ fontSize: 12, flex: 1 }}>Saving Throw</Text>
          <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold', width: 16, textAlign: 'right' }}>
            {saveBonus(c, ab)}
          </Text>
        </View>
        {skills.map((sk) => (
          <View key={sk.id} style={[s.row, { alignItems: 'center', paddingLeft: 2, marginTop: 1 }]}>
            <Text style={s.dot}>{profs.has(sk.id) ? '●' : '○'}</Text>
            <Text style={{ fontSize: 12, flex: 1 }}>{sk.label}</Text>
            <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold', width: 16, textAlign: 'right' }}>
              {skillBonus(c, sk.id, sk.ability)}
            </Text>
          </View>
        ))}
      </View>
    );
  };
}
