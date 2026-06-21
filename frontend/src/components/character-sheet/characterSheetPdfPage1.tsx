import type { Character } from '../../types';
import { displayLabel, displayLabels, EMPTY_FIELD } from '../../lib/displayText';
import { formatMod, initiativeMod, passivePerception, proficiencyBonus, spellAttackBonus } from './sheetUtils';
import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';
import { classLine, weaponAttack } from './characterSheetPdfUtils';
import { createPdfParts } from './characterSheetPdfParts';
import { createPdfShapes, formatHitDice, stackLabel } from './characterSheetPdfShapes';

type UnlockedFeatures = {
  class_features?: Record<string, string[]>;
  subclass_features?: Record<string, string[]>;
  species_traits?: Array<{ id: string; label: string; detail?: string; display: string }>;
  resolved_choices?: Array<{ id: string; label: string; value_label: string }>;
};

export function buildSheetPage1(pdf: PdfModule, c: Character, unlockedFeatures?: UnlockedFeatures) {
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
  const classFeatureLines = Object.entries(unlockedFeatures?.class_features || {}).flatMap(([cid, feats]) =>
    (feats as string[]).map((f) => `${displayLabel(cid)}: ${displayLabel(f)}`),
  );
  const subclassFeatureLines = Object.entries(unlockedFeatures?.subclass_features || {}).flatMap(([key, feats]) =>
    (feats as string[]).map((f) => `${displayLabel(key)}: ${displayLabel(f)}`),
  );
  const features = [
    ...classFeatureLines,
    ...subclassFeatureLines,
    ...(unlockedFeatures?.resolved_choices || []).map((row) => `${row.label}: ${row.value_label}`),
    c.origin_feat ? `Origin Feat: ${displayLabel(c.origin_feat)}` : '',
    c.versatile_origin_feat ? `Versatile Feat: ${displayLabel(c.versatile_origin_feat)}` : '',
    ...(c.feats || []).map((f) => displayLabel(f)),
    c.wild_shape_uses ? `Wild Shape: ${c.wild_shape_uses} uses` : '',
  ].filter(Boolean);
  const hitDie = c.hit_die ?? 8;

  return (
    <Page size="LETTER" style={s.page} wrap={false}>
      <View style={[s.row, s.box, { marginBottom: 2 }]}>
        <HeaderField label="Character Name" value={c.name || ''} flex={1.35} />
        <HeaderField label="Background" value={displayLabel(c.background)} flex={0.85} />
        <HeaderField label="Class" value={classLine(c)} flex={1} />
        <HeaderField label="Species" value={displayLabel(c.species)} flex={0.65} />
        <HeaderField label="Subclass" value={displayLabel(c.subclass)} flex={0.85} />
        <View style={{ width: 38, alignItems: 'center', justifyContent: 'center', borderRight: '0.5pt solid #999' }}>
          <Text style={s.labelSm}>Level</Text>
          <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold' }} wrap={false}>
            {c.level || 1}
          </Text>
          <Text style={[s.labelSm, { marginTop: 1 }]}>XP</Text>
          <Text style={{ fontSize: 8 }} wrap={false}>
            {c.xp || 0}
          </Text>
        </View>
      </View>

      <View style={[s.combatRow, s.box, { marginBottom: 3, padding: 3, gap: 3 }]}>
        <View style={{ width: 46, alignItems: 'center', justifyContent: 'center' }}>
          <Text style={[s.labelSm, { marginBottom: 2 }]}>Armor Class</Text>
          <View style={s.shield}>
            <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold' }} wrap={false}>
              {c.ac ?? 10}
            </Text>
          </View>
        </View>

        <View style={{ flex: 1.2, minWidth: 0 }}>
          <Text style={[s.labelSm, { marginBottom: 2 }]}>Hit Points</Text>
          <View style={[s.row, { gap: 3 }]}>
            {[
              { label: 'Cur', value: String(c.hp ?? 0) },
              { label: 'Max', value: String(c.max_hp ?? 0) },
              { label: 'Tmp', value: ' ' },
            ].map((cell) => (
              <View key={cell.label} style={[s.miniStatBox, { flex: 1 }]}>
                <Text style={s.miniStatLabel}>{cell.label}</Text>
                <Text style={s.miniStatValue} wrap={false}>
                  {cell.value}
                </Text>
              </View>
            ))}
          </View>
        </View>

        <View style={{ width: 78 }}>
          <Text style={[s.labelSm, { marginBottom: 2 }]}>Hit Dice</Text>
          <View style={[s.row, { gap: 3 }]}>
            <View style={[s.miniStatBox, { flex: 1 }]}>
              <Text style={s.miniStatLabel}>Spent</Text>
              <Text style={s.miniStatValue} wrap={false}>
                {hitDiceSpent}
              </Text>
            </View>
            <View style={[s.miniStatBox, { flex: 1.15 }]}>
              <Text style={s.miniStatLabel}>Max</Text>
              <Text style={s.miniStatValue} wrap={false}>
                {formatHitDice(hitDiceMax, hitDie)}
              </Text>
            </View>
          </View>
        </View>

        <View style={{ width: 62 }}>
          <Text style={[s.labelSm, { marginBottom: 2 }]}>Death Saves</Text>
          <Text style={{ fontSize: 6, marginBottom: 1 }}>Successes</Text>
          <DiamondRow count={3} filled={Number(c.death_save_successes ?? 0)} />
          <Text style={{ fontSize: 6, marginTop: 2, marginBottom: 1 }}>Failures</Text>
          <DiamondRow count={3} filled={Number(c.death_save_failures ?? 0)} />
        </View>

        <View style={[s.miniStatBox, { width: 52, alignSelf: 'stretch' }]}>
          <Text style={s.miniStatLabel}>Prof</Text>
          <Text style={s.miniStatValue} wrap={false}>
            {formatMod(pb)}
          </Text>
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
            <Text style={{ fontSize: 10, fontFamily: 'Helvetica-Bold', marginTop: 1 }} wrap={false}>
              {stat.value}
            </Text>
          </View>
        ))}
        <View style={[s.box, { flex: 0.8, padding: 3, alignItems: 'center', justifyContent: 'center' }]}>
          <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', letterSpacing: 0.8 }}>D&D</Text>
        </View>
      </View>

      <View style={[s.row, { gap: 3, alignItems: 'stretch' }]}>
        <View style={{ width: 108 }}>
          <View style={[s.box, { padding: 3, marginBottom: 2, alignItems: 'center' }]}>
            <Text style={s.labelSm}>Heroic Inspiration</Text>
            <View style={{ marginTop: 2 }}>
              <CirclePip filled={!!c.heroic_inspiration} size={8} />
            </View>
          </View>
          {ABILITIES.map((ab) => (
            <AbilityBlock key={ab} ab={ab} c={c} profs={profs} saves={saveProfs} />
          ))}
          <Box title="Equipment Training & Proficiencies" style={{ padding: 4, marginTop: 1 }}>
            <Text style={[s.labelSm, { marginBottom: 1 }]}>Armor</Text>
            <Text style={{ fontSize: 7, marginBottom: 3, lineHeight: 1.25 }}>
              {displayLabel(String(c.armor || ''))}
              {c.shield ? ' · Shield' : ''}
            </Text>
            <Text style={[s.labelSm, { marginBottom: 1 }]}>Weapons</Text>
            <Text style={{ fontSize: 7, marginBottom: 3, lineHeight: 1.25 }}>
              {displayLabels(
                (c.weapons || []).map((w) => w.name),
                ', ',
              ) || EMPTY_FIELD}
            </Text>
            <Text style={[s.labelSm, { marginBottom: 1 }]}>Tools</Text>
            <Text style={{ fontSize: 7, lineHeight: 1.25 }}>
              {displayLabels([...new Set((c.tool_proficiencies as string[] | undefined) || [])], ', ') || EMPTY_FIELD}
            </Text>
          </Box>
        </View>

        <View style={{ flex: 1 }}>
          <Box title="Weapons & Damage Cantrips" style={{ marginBottom: 3 }}>
            <View style={s.tableHeader}>
              <Text style={[s.labelSm, { width: '30%' }]}>Name</Text>
              <Text style={[s.labelSm, { width: '14%' }]}>Atk</Text>
              <Text style={[s.labelSm, { width: '26%' }]}>Damage</Text>
              <Text style={[s.labelSm, { flex: 1 }]}>Notes</Text>
            </View>
            {(attackRows.length ? attackRows : [{ id: 'empty', name: '', atk: '', damage: '', notes: '' }])
              .slice(0, 6)
              .map((row) => (
                <View key={row.id} style={s.tableRow}>
                  <Text style={[s.tableCell, { width: '30%' }]}>{row.name}</Text>
                  <Text style={[s.tableCell, { width: '14%' }]} wrap={false}>
                    {row.atk}
                  </Text>
                  <Text style={[s.tableCell, { width: '26%' }]}>{row.damage}</Text>
                  <Text style={[s.tableCell, { flex: 1 }]}>{row.notes}</Text>
                </View>
              ))}
            {Array.from({ length: Math.max(0, 6 - attackRows.length) }).map((_, i) => (
              <View key={`attack-placeholder-${i}`} style={s.tableRow}>
                <Text style={[s.tableCell, { width: '30%' }]}> </Text>
                <Text style={[s.tableCell, { width: '14%' }]}> </Text>
                <Text style={[s.tableCell, { width: '26%' }]}> </Text>
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
                {(unlockedFeatures?.species_traits || []).length ? (
                  (unlockedFeatures?.species_traits || []).map((row) => (
                    <Text key={row.id} style={{ fontSize: 7.5, marginBottom: 2 }}>
                      • {row.display}
                    </Text>
                  ))
                ) : (
                  <Text style={{ fontSize: 7.5, fontFamily: 'Helvetica-Bold' }}>{displayLabel(c.species)}</Text>
                )}
              </View>
            </Box>
            <Box title="Feats" style={{ flex: 1, minHeight: 64 }}>
              <View style={[s.gridBg, { padding: 4, minHeight: 48 }]}>
                <Text style={{ fontSize: 7.5 }}>
                  {displayLabels(
                    [c.origin_feat, c.versatile_origin_feat, ...(c.feats || [])].filter(Boolean) as string[],
                    '\n',
                  ) || EMPTY_FIELD}
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
