import type { Character } from '../../types';
import { displayLabel, displayLabels, EMPTY_FIELD } from '../../lib/displayText';
import {
  formatMod,
  initiativeMod,
  passivePerception,
  proficiencyBonus,
  spellAttackBonus,
} from './sheetUtils';
import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';
import { classLine, weaponAttack } from './characterSheetPdfUtils';
import { createPdfParts } from './characterSheetPdfParts';

export function buildSheetPage1(pdf: PdfModule, c: Character) {
  const { Page, Text, View } = pdf;
  const { Box, DiamondRow, AbilityBlock, HeaderField, ABILITIES } = createPdfParts(pdf);
  const profs = new Set(c.skill_proficiencies || []);
  const saveProfs = new Set(c.save_proficiencies || []);
  const pb = proficiencyBonus(c.level || 1);
  const hitDiceMax = Number(c.hit_dice_max ?? c.level ?? 1);
  const hitDiceSpent = Number(c.hit_dice_spent ?? 0);
  const spellAtk = spellAttackBonus(c);
  const cantripRows = (c.cantrips || []).map((name) => ({
    id: `cantrip-${name}`,
    name: displayLabel(name),
    atk: spellAtk !== null ? formatMod(spellAtk) : EMPTY_FIELD,
    damage: 'Cantrip',
    notes: '',
  }));
  const weaponRows = (c.weapons || []).map((w) => ({
    id: `weapon-${w.name}`,
    name: displayLabel(w.name),
    atk: weaponAttack(c, w),
    damage: [w.damage, w.damage_type].filter(Boolean).join(' '),
    notes: '',
  }));
  const attackRows = [...weaponRows, ...cantripRows];
  const features = [
    classLine(c),
    c.origin_feat ? `Origin Feat: ${displayLabel(c.origin_feat)}` : '',
    ...(c.feats || []).map((f) => displayLabel(f)),
    c.wild_shape_uses ? `Wild Shape: ${c.wild_shape_uses} uses` : '',
  ].filter(Boolean);

  return (
    <Page size="LETTER" style={s.page}>
      <View style={[s.row, s.box, { marginBottom: 4 }]}>
        <HeaderField label="Character Name" value={c.name || ''} flex={1.4} />
        <HeaderField label="Background" value={displayLabel(c.background)} flex={0.9} />
        <HeaderField label="Class" value={classLine(c)} flex={1.1} />
        <HeaderField label="Species" value={displayLabel(c.species)} flex={0.7} />
        <HeaderField label="Subclass" value={displayLabel(c.subclass)} flex={0.9} />
        <View style={{ width: 42, alignItems: 'center', justifyContent: 'center', borderRight: '0.5pt solid #ccc' }}>
          <Text style={s.labelSm}>Level</Text>
          <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold' }}>{c.level || 1}</Text>
          <Text style={s.labelSm}>XP</Text>
          <Text style={{ fontSize: 12 }}>{c.xp || 0}</Text>
        </View>
        <View style={{ width: 44, alignItems: 'center', padding: 3, borderRight: '0.5pt solid #ccc' }}>
          <Text style={s.labelSm}>Armor Class</Text>
          <View style={s.shield}>
            <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold' }}>{c.ac ?? 10}</Text>
          </View>
        </View>
        <View style={{ flex: 1, padding: 3, borderRight: '0.5pt solid #ccc' }}>
          <Text style={s.labelSm}>Hit Points</Text>
          <View style={[s.row, { marginTop: 2, gap: 3 }]}>
            <View style={[s.box, { flex: 1, padding: 2, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Current</Text>
              <Text style={s.valueLg}>{c.hp ?? 0}</Text>
            </View>
            <View style={[s.box, { flex: 1, padding: 2, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Max</Text>
              <Text style={s.valueLg}>{c.max_hp ?? 0}</Text>
            </View>
            <View style={[s.box, { flex: 0.7, padding: 2, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Temp</Text>
              <Text style={s.valueLg}> </Text>
            </View>
          </View>
        </View>
        <View style={{ width: 52, padding: 3, borderRight: '0.5pt solid #ccc' }}>
          <Text style={s.labelSm}>Hit Dice</Text>
          <View style={[s.row, { marginTop: 2, gap: 2 }]}>
            <View style={[s.box, { flex: 1, padding: 2, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Spent</Text>
              <Text style={{ fontSize: 12 }}>{hitDiceSpent}</Text>
            </View>
            <View style={[s.box, { flex: 1, padding: 2, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Max</Text>
              <Text style={{ fontSize: 12 }}>
                {hitDiceMax}d{c.hit_die ?? 8}
              </Text>
            </View>
          </View>
        </View>
        <View style={{ width: 58, padding: 3 }}>
          <Text style={s.labelSm}>Death Saves</Text>
          <Text style={{ fontSize: 12, marginTop: 2 }}>Successes</Text>
          <DiamondRow count={3} filled={Number(c.death_save_successes ?? 0)} />
          <Text style={{ fontSize: 12, marginTop: 2 }}>Failures</Text>
          <DiamondRow count={3} filled={Number(c.death_save_failures ?? 0)} />
        </View>
      </View>

      <View style={[s.row, { gap: 4, marginBottom: 4 }]}>
        {[
          { label: 'Initiative', value: formatMod(initiativeMod(c)) },
          { label: 'Speed', value: `${c.speed ?? 30} ft` },
          { label: 'Size', value: displayLabel(String(c.size || 'medium')) },
          { label: 'Passive Perception', value: String(passivePerception(c)) },
        ].map((stat) => (
          <View key={stat.label} style={[s.box, { flex: 1, padding: 4, alignItems: 'center' }]}>
            <Text style={s.labelSm}>{stat.label}</Text>
            <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold', marginTop: 2 }}>{stat.value}</Text>
          </View>
        ))}
        <View style={[s.box, { flex: 1.2, padding: 4, alignItems: 'center', justifyContent: 'center' }]}>
          <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold', letterSpacing: 1 }}>D&D</Text>
        </View>
      </View>

      <View style={[s.row, { flex: 1, gap: 4, alignItems: 'stretch' }]}>
        <View style={{ width: 118 }}>
          <View style={[s.box, { padding: 4, marginBottom: 3, alignItems: 'center' }]}>
            <Text style={s.labelSm}>Proficiency Bonus</Text>
            <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold' }}>{formatMod(pb)}</Text>
          </View>
          {ABILITIES.map((ab) => (
            <AbilityBlock key={ab} ab={ab} c={c} profs={profs} saves={saveProfs} />
          ))}
          <View style={[s.box, { padding: 4, marginTop: 2, alignItems: 'center' }]}>
            <Text style={s.labelSm}>Heroic Inspiration</Text>
            <Text style={{ fontSize: 12, marginTop: 2 }}>{c.heroic_inspiration ? '★' : '☆'}</Text>
          </View>
          <Box title="Equipment Training & Proficiencies" style={{ marginTop: 3, padding: 4, flex: 1 }}>
            <Text style={s.labelSm}>Armor</Text>
            <Text style={{ fontSize: 12, marginBottom: 3 }}>
              {displayLabel(String(c.armor || ''))}
              {c.shield ? ' · Shield' : ''}
            </Text>
            <Text style={s.labelSm}>Weapons</Text>
            <Text style={{ fontSize: 12, marginBottom: 3 }}>
              {displayLabels(
                (c.weapons || []).map((w) => w.name),
                ', ',
              ) || EMPTY_FIELD}
            </Text>
            <Text style={s.labelSm}>Tools</Text>
            <Text style={{ fontSize: 12 }}>
              {displayLabels((c.tool_proficiencies as string[] | undefined) || [], ', ') || EMPTY_FIELD}
            </Text>
          </Box>
        </View>

        <View style={{ flex: 1 }}>
          <Box title="Weapons & Damage Cantrips" style={{ marginBottom: 4 }}>
            <View style={s.tableHeader}>
              <Text style={[s.labelSm, { width: '28%' }]}>Name</Text>
              <Text style={[s.labelSm, { width: '18%' }]}>Atk Bonus / DC</Text>
              <Text style={[s.labelSm, { width: '24%' }]}>Damage & Type</Text>
              <Text style={[s.labelSm, { flex: 1 }]}>Notes</Text>
            </View>
            {(attackRows.length ? attackRows : [{ id: 'empty', name: '', atk: '', damage: '', notes: '' }])
              .slice(0, 6)
              .map((row) => (
                <View key={row.id} style={s.tableRow}>
                  <Text style={{ width: '28%', fontSize: 12 }}>{row.name}</Text>
                  <Text style={{ width: '18%', fontSize: 12 }}>{row.atk}</Text>
                  <Text style={{ width: '24%', fontSize: 12 }}>{row.damage}</Text>
                  <Text style={{ flex: 1, fontSize: 12 }}>{row.notes}</Text>
                </View>
              ))}
            {['a', 'b', 'c', 'd'].slice(0, Math.max(0, 4 - attackRows.length)).map((slot) => (
              <View key={`attack-placeholder-${slot}`} style={s.tableRow}>
                <Text style={{ width: '28%' }}> </Text>
                <Text style={{ width: '18%' }}> </Text>
                <Text style={{ width: '24%' }}> </Text>
                <Text style={{ flex: 1 }}> </Text>
              </View>
            ))}
          </Box>

          <Box title="Class Features" style={{ marginBottom: 4, minHeight: 200 }}>
            <View style={[s.gridBg, { padding: 6, minHeight: 190 }]}>
              {features.length ? (
                features.map((line) => (
                  <Text key={`feature-${line.slice(0, 40)}-${line.length}`} style={{ fontSize: 12, marginBottom: 3 }}>
                    • {line}
                  </Text>
                ))
              ) : (
                <Text style={{ fontSize: 12, color: '#888' }}> </Text>
              )}
            </View>
          </Box>

          <View style={[s.row, { gap: 4 }]}>
            <Box title="Species Traits" style={{ flex: 1, minHeight: 90 }}>
              <View style={[s.gridBg, { padding: 6, minHeight: 72 }]}>
                <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold' }}>{displayLabel(c.species)}</Text>
              </View>
            </Box>
            <Box title="Feats" style={{ flex: 1, minHeight: 90 }}>
              <View style={[s.gridBg, { padding: 6, minHeight: 72 }]}>
                <Text style={{ fontSize: 12 }}>
                  {displayLabels([c.origin_feat, ...(c.feats || [])].filter(Boolean) as string[], '\n') ||
                    EMPTY_FIELD}
                </Text>
              </View>
            </Box>
          </View>
        </View>
      </View>

      <Text style={s.footer}>Auto-DM · D&D 5e (2024) character sheet · 1 of 2</Text>
    </Page>
  );
}
