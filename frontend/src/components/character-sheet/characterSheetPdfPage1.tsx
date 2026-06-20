import type { Character } from '../../types';
import { displayLabel, displayLabels, EMPTY_FIELD } from '../../lib/displayText';
import { formatMod, initiativeMod, passivePerception, proficiencyBonus, spellAttackBonus } from './sheetUtils';
import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';
import { classLine, weaponAttack } from './characterSheetPdfUtils';
import { createPdfParts } from './characterSheetPdfParts';
import { createPdfShapes, stackLabel } from './characterSheetPdfShapes';

export function buildSheetPage1(pdf: PdfModule, c: Character) {
  const { Page, Text, View } = pdf;
  const { Box, DiamondRow, AbilityBlock, HeaderField, ABILITIES } = createPdfParts(pdf);
  const { CirclePip } = createPdfShapes(pdf);
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
    <Page size="LETTER" style={s.page} wrap={false}>
      <View style={[s.row, s.box, { marginBottom: 3 }]}>
        <HeaderField label="Character Name" value={c.name || ''} flex={1.35} />
        <HeaderField label="Background" value={displayLabel(c.background)} flex={0.85} />
        <HeaderField label="Class" value={classLine(c)} flex={1} />
        <HeaderField label="Species" value={displayLabel(c.species)} flex={0.65} />
        <HeaderField label="Subclass" value={displayLabel(c.subclass)} flex={0.85} />
        <View style={{ width: 36, alignItems: 'center', justifyContent: 'center', borderRight: '0.5pt solid #999' }}>
          <Text style={s.labelSm}>Level</Text>
          <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold' }}>{c.level || 1}</Text>
          <Text style={[s.labelSm, { marginTop: 1 }]}>XP</Text>
          <Text style={{ fontSize: 8 }}>{c.xp || 0}</Text>
        </View>
        <View style={{ width: 40, alignItems: 'center', padding: 2, borderRight: '0.5pt solid #999' }}>
          <Text style={s.labelSm}>{stackLabel('Armor Class')}</Text>
          <View style={s.shield}>
            <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold' }}>{c.ac ?? 10}</Text>
          </View>
        </View>
        <View style={{ flex: 1, padding: 2, borderRight: '0.5pt solid #999', minWidth: 0 }}>
          <Text style={s.labelSm}>{stackLabel('Hit Points')}</Text>
          <View style={[s.row, { marginTop: 1, gap: 2 }]}>
            <View style={[s.box, { flex: 1, padding: 1, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Current</Text>
              <Text style={s.valueLg}>{c.hp ?? 0}</Text>
            </View>
            <View style={[s.box, { flex: 1, padding: 1, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Max</Text>
              <Text style={s.valueLg}>{c.max_hp ?? 0}</Text>
            </View>
            <View style={[s.box, { flex: 0.65, padding: 1, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Temp</Text>
              <Text style={s.valueLg}> </Text>
            </View>
          </View>
        </View>
        <View style={{ width: 48, padding: 2, borderRight: '0.5pt solid #999' }}>
          <Text style={s.labelSm}>{stackLabel('Hit Dice')}</Text>
          <View style={[s.row, { marginTop: 1, gap: 1 }]}>
            <View style={[s.box, { flex: 1, padding: 1, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Spent</Text>
              <Text style={{ fontSize: 8 }}>{hitDiceSpent}</Text>
            </View>
            <View style={[s.box, { flex: 1, padding: 1, alignItems: 'center' }]}>
              <Text style={s.labelSm}>Max</Text>
              <Text style={{ fontSize: 8 }}>
                {hitDiceMax}d{c.hit_die ?? 8}
              </Text>
            </View>
          </View>
        </View>
        <View style={{ width: 52, padding: 2 }}>
          <Text style={s.labelSm}>{stackLabel('Death Saves')}</Text>
          <Text style={{ fontSize: 6, marginTop: 1 }}>Successes</Text>
          <DiamondRow count={3} filled={Number(c.death_save_successes ?? 0)} />
          <Text style={{ fontSize: 6, marginTop: 1 }}>Failures</Text>
          <DiamondRow count={3} filled={Number(c.death_save_failures ?? 0)} />
        </View>
      </View>

      <View style={[s.row, { gap: 3, marginBottom: 3 }]}>
        {[
          { label: 'Initiative', value: formatMod(initiativeMod(c)) },
          { label: 'Speed', value: `${c.speed ?? 30} ft` },
          { label: 'Size', value: displayLabel(String(c.size || 'medium')) },
          { label: 'Passive Perception', value: String(passivePerception(c)) },
        ].map((stat) => (
          <View key={stat.label} style={[s.box, { flex: 1, padding: 3, alignItems: 'center' }]}>
            <Text style={s.labelSm}>{stackLabel(stat.label)}</Text>
            <Text style={{ fontSize: 10, fontFamily: 'Helvetica-Bold', marginTop: 1 }}>{stat.value}</Text>
          </View>
        ))}
        <View style={[s.box, { flex: 0.8, padding: 3, alignItems: 'center', justifyContent: 'center' }]}>
          <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', letterSpacing: 0.8 }}>D&D</Text>
        </View>
      </View>

      <View style={[s.row, { gap: 3, alignItems: 'stretch' }]}>
        <View style={{ width: 108 }}>
          <View style={[s.box, { padding: 3, marginBottom: 2, alignItems: 'center' }]}>
            <Text style={s.labelSm}>{stackLabel('Proficiency Bonus')}</Text>
            <Text style={{ fontSize: 10, fontFamily: 'Helvetica-Bold' }}>{formatMod(pb)}</Text>
          </View>
          {ABILITIES.map((ab) => (
            <AbilityBlock key={ab} ab={ab} c={c} profs={profs} saves={saveProfs} />
          ))}
          <View style={[s.box, { padding: 3, marginTop: 1, marginBottom: 2, alignItems: 'center' }]}>
            <Text style={s.labelSm}>{stackLabel('Heroic Inspiration')}</Text>
            <View style={{ marginTop: 2 }}>
              <CirclePip filled={!!c.heroic_inspiration} size={8} />
            </View>
          </View>
          <Box title="Equipment Training & Proficiencies" style={{ padding: 3 }}>
            <Text style={s.labelSm}>Armor</Text>
            <Text style={{ fontSize: 7, marginBottom: 2 }}>
              {displayLabel(String(c.armor || ''))}
              {c.shield ? ' · Shield' : ''}
            </Text>
            <Text style={s.labelSm}>Weapons</Text>
            <Text style={{ fontSize: 7, marginBottom: 2 }}>
              {displayLabels(
                (c.weapons || []).map((w) => w.name),
                ', ',
              ) || EMPTY_FIELD}
            </Text>
            <Text style={s.labelSm}>Tools</Text>
            <Text style={{ fontSize: 7 }}>
              {displayLabels([...new Set((c.tool_proficiencies as string[] | undefined) || [])], ', ') || EMPTY_FIELD}
            </Text>
          </Box>
        </View>

        <View style={{ flex: 1 }}>
          <Box title="Weapons & Damage Cantrips" style={{ marginBottom: 3 }}>
            <View style={s.tableHeader}>
              <Text style={[s.labelSm, { width: '28%' }]}>Name</Text>
              <Text style={[s.labelSm, { width: '18%' }]}>{stackLabel('Atk Bonus / DC')}</Text>
              <Text style={[s.labelSm, { width: '24%' }]}>{stackLabel('Damage & Type')}</Text>
              <Text style={[s.labelSm, { flex: 1 }]}>Notes</Text>
            </View>
            {(attackRows.length ? attackRows : [{ id: 'empty', name: '', atk: '', damage: '', notes: '' }])
              .slice(0, 6)
              .map((row) => (
                <View key={row.id} style={s.tableRow}>
                  <Text style={[s.tableCell, { width: '28%' }]}>{row.name}</Text>
                  <Text style={[s.tableCell, { width: '18%' }]}>{row.atk}</Text>
                  <Text style={[s.tableCell, { width: '24%' }]}>{row.damage}</Text>
                  <Text style={[s.tableCell, { flex: 1 }]}>{row.notes}</Text>
                </View>
              ))}
            {Array.from({ length: Math.max(0, 6 - attackRows.length) }).map((_, i) => (
              <View key={`attack-placeholder-${i}`} style={s.tableRow}>
                <Text style={[s.tableCell, { width: '28%' }]}> </Text>
                <Text style={[s.tableCell, { width: '18%' }]}> </Text>
                <Text style={[s.tableCell, { width: '24%' }]}> </Text>
                <Text style={[s.tableCell, { flex: 1 }]}> </Text>
              </View>
            ))}
          </Box>

          <Box title="Class Features" style={{ marginBottom: 3, minHeight: 118 }}>
            <View style={[s.gridBg, { padding: 4, minHeight: 100 }]}>
              {features.length ? (
                features.map((line) => (
                  <Text key={`feature-${line.slice(0, 40)}-${line.length}`} style={{ fontSize: 7.5, marginBottom: 2 }}>
                    • {line}
                  </Text>
                ))
              ) : (
                <Text style={{ fontSize: 7.5, color: '#888' }}> </Text>
              )}
            </View>
          </Box>

          <View style={[s.row, { gap: 3 }]}>
            <Box title="Species Traits" style={{ flex: 1, minHeight: 64 }}>
              <View style={[s.gridBg, { padding: 4, minHeight: 48 }]}>
                <Text style={{ fontSize: 7.5, fontFamily: 'Helvetica-Bold' }}>{displayLabel(c.species)}</Text>
              </View>
            </Box>
            <Box title="Feats" style={{ flex: 1, minHeight: 64 }}>
              <View style={[s.gridBg, { padding: 4, minHeight: 48 }]}>
                <Text style={{ fontSize: 7.5 }}>
                  {displayLabels([c.origin_feat, ...(c.feats || [])].filter(Boolean) as string[], '\n') || EMPTY_FIELD}
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
