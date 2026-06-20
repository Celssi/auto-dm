import type { Character } from '../../types';
import { displayLabel, displayLabels, EMPTY_FIELD } from '../../lib/displayText';
import { abilityMod, formatMod, spellAttackBonus, spellAbility, spellSaveDc } from './sheetUtils';
import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';
import { splitNotes } from './characterSheetPdfUtils';
import { createPdfParts } from './characterSheetPdfParts';
import { createPdfShapes, stackLabel } from './characterSheetPdfShapes';

export function buildSheetPage2(pdf: PdfModule, c: Character) {
  const { Page, Text, View } = pdf;
  const { Box } = createPdfParts(pdf);
  const { CirclePip, PipRow } = createPdfShapes(pdf);
  const spellAb = spellAbility(c.class_name || '');
  const spellDc = spellSaveDc(c);
  const spellAtk = spellAttackBonus(c);
  const spellMod = spellAb ? formatMod(abilityMod(c.ability_scores?.[spellAb] ?? 10)) : EMPTY_FIELD;
  const prepared = c.prepared_spells?.length ? c.prepared_spells : c.known_spells || [];
  const notesText = String(c.appearance || c.equipment_notes || '');
  const { appearance, backstory } = splitNotes(notesText);
  const attuned = (c.attuned_items as string[] | undefined) || [];
  const slots = c.spell_slots || {};
  const spellRows = [
    ...(c.cantrips || []).map((n) => ({ name: n, level: 'C' })),
    ...prepared.map((n) => ({ name: n, level: '' })),
  ];
  const spellRowCount = Math.min(spellRows.length, 18);
  const spellPlaceholders = Math.max(0, 18 - spellRowCount);

  return (
    <Page size="LETTER" style={s.page} wrap={false}>
      <View style={[s.row, { gap: 3, marginBottom: 3 }]}>
        <View style={[s.box, { width: 100, padding: 3 }]}>
          <Text style={[s.label, { marginBottom: 3 }]}>Spellcasting</Text>
          <View style={[s.row, { justifyContent: 'space-between', marginBottom: 2 }]}>
            <Text style={s.labelSm}>Modifier</Text>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold' }}>{spellMod}</Text>
          </View>
          <View style={[s.row, { justifyContent: 'space-between', marginBottom: 2 }]}>
            <Text style={s.labelSm}>{stackLabel('Spell Save DC')}</Text>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold' }}>{spellDc ?? EMPTY_FIELD}</Text>
          </View>
          <View style={[s.row, { justifyContent: 'space-between' }]}>
            <Text style={s.labelSm}>{stackLabel('Spell Attack')}</Text>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold' }}>
              {spellAtk !== null ? formatMod(spellAtk) : EMPTY_FIELD}
            </Text>
          </View>
          {spellAb ? (
            <Text style={{ fontSize: 6, marginTop: 3, color: '#555' }}>
              {stackLabel('Spellcasting Ability')}: {spellAb.toUpperCase()}
            </Text>
          ) : null}
        </View>

        <Box title="Spell Slots" style={{ flex: 1 }}>
          <View style={[s.row, { padding: 3, gap: 1 }]}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((lvl) => {
              const max = slots[String(lvl)] ?? 0;
              const remaining = max;
              const expended = Math.max(0, max - remaining);
              return (
                <View key={lvl} style={{ flex: 1, alignItems: 'center', minWidth: 0 }}>
                  <Text style={s.labelSm}>L{lvl}</Text>
                  <Text style={{ fontSize: 6, marginTop: 1 }}>Total</Text>
                  <PipRow count={Math.max(max, max > 0 ? max : 1)} filled={remaining} gap={1} />
                  <Text style={{ fontSize: 6, marginTop: 1 }}>Expended</Text>
                  <Text style={{ fontSize: 7 }}>
                    {expended}/{max || 0}
                  </Text>
                </View>
              );
            })}
          </View>
        </Box>
      </View>

      <View style={[s.row, { gap: 3, alignItems: 'stretch' }]}>
        <Box title="Cantrips & Prepared Spells" style={{ flex: 1.55 }}>
          <View style={s.tableHeader}>
            <Text style={[s.labelSm, { width: 18 }]}>Level</Text>
            <Text style={[s.labelSm, { width: '24%' }]}>Name</Text>
            <Text style={[s.labelSm, { width: '14%' }]}>{stackLabel('Casting Time')}</Text>
            <Text style={[s.labelSm, { width: '12%' }]}>Range</Text>
            <Text style={[s.labelSm, { width: '16%' }]}>C / R / M</Text>
            <Text style={[s.labelSm, { flex: 1 }]}>Notes</Text>
          </View>
          {spellRows.slice(0, spellRowCount).map((sp) => (
            <View key={`spell-${sp.name}-${sp.level}`} style={s.tableRow}>
              <Text style={[s.tableCell, { width: 18 }]}>{sp.level}</Text>
              <Text style={[s.tableCell, { width: '24%' }]}>{displayLabel(sp.name)}</Text>
              <Text style={[s.tableCell, { width: '14%' }]}> </Text>
              <Text style={[s.tableCell, { width: '12%' }]}> </Text>
              <View style={[s.row, { width: '16%', gap: 2, alignItems: 'center' }]}>
                <CirclePip filled={false} />
                <CirclePip filled={false} />
                <CirclePip filled={false} />
              </View>
              <Text style={[s.tableCell, { flex: 1 }]}> </Text>
            </View>
          ))}
          {Array.from({ length: spellPlaceholders }).map((_, i) => (
            <View key={`spell-placeholder-${i}`} style={s.tableRow}>
              <Text style={[s.tableCell, { width: 18 }]}> </Text>
              <Text style={[s.tableCell, { width: '24%' }]}> </Text>
              <Text style={[s.tableCell, { width: '14%' }]}> </Text>
              <Text style={[s.tableCell, { width: '12%' }]}> </Text>
              <Text style={[s.tableCell, { width: '16%' }]}> </Text>
              <Text style={[s.tableCell, { flex: 1 }]}> </Text>
            </View>
          ))}
        </Box>

        <View style={{ width: 156 }}>
          <Box title="Appearance" style={{ marginBottom: 3, minHeight: 58 }}>
            <View style={{ padding: 4, minHeight: 44 }}>
              <Text style={{ fontSize: 7.5, lineHeight: 1.2 }}>{appearance || ' '}</Text>
            </View>
          </Box>
          <Box title="Backstory & Personality" style={{ marginBottom: 3, minHeight: 96 }}>
            <View style={[s.gridBg, { padding: 4, minHeight: 68 }]}>
              <Text style={{ fontSize: 7.5, lineHeight: 1.2 }}>{backstory || ' '}</Text>
            </View>
            <View style={{ borderTop: '0.5pt solid #000', padding: 3 }}>
              <Text style={s.labelSm}>Alignment</Text>
              <Text style={{ fontSize: 7.5, marginTop: 1 }}>{c.alignment || ' '}</Text>
            </View>
          </Box>
          <Box title="Languages" style={{ marginBottom: 3, minHeight: 36 }}>
            <View style={[s.gridBg, { padding: 4 }]}>
              <Text style={{ fontSize: 7.5 }}>
                {displayLabels((c.languages as string[] | undefined) || ['Common'], ', ')}
              </Text>
            </View>
          </Box>
          <Box title="Equipment" style={{ marginBottom: 3, minHeight: 88 }}>
            <View style={[s.gridBg, { padding: 4, minHeight: 52 }]}>
              {(c.inventory || []).slice(0, 8).map((item) => (
                <Text key={`inv-${item}`} style={{ fontSize: 7.5, marginBottom: 1 }}>
                  • {displayLabel(item)}
                </Text>
              ))}
            </View>
            <View style={{ borderTop: '0.5pt solid #000', padding: 3 }}>
              <Text style={s.labelSm}>{stackLabel('Magic Item Attunement')}</Text>
              {[0, 1, 2].map((i) => (
                <View key={`attuned-slot-${i}`} style={[s.row, { alignItems: 'center', marginTop: 1, gap: 3 }]}>
                  <CirclePip filled={!!attuned[i]} />
                  <Text style={{ fontSize: 7.5, flex: 1 }}>{attuned[i] ? displayLabel(attuned[i]) : ' '}</Text>
                </View>
              ))}
            </View>
          </Box>
          <Box title="Coins">
            <View style={[s.row, { padding: 3 }]}>
              {(['cp', 'sp', 'ep', 'gp', 'pp'] as const).map((k) => (
                <View
                  key={k}
                  style={{ flex: 1, alignItems: 'center', borderRight: k !== 'pp' ? '0.5pt solid #ccc' : undefined }}
                >
                  <Text style={s.labelSm}>{k.toUpperCase()}</Text>
                  <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', marginTop: 1 }}>
                    {c.currency?.[k] || 0}
                  </Text>
                </View>
              ))}
            </View>
          </Box>
        </View>
      </View>

      {c.concentration ? (
        <View style={[s.box, { marginTop: 3, padding: 3 }]}>
          <Text style={s.labelSm}>Concentration</Text>
          <Text style={{ fontSize: 7.5 }}>{displayLabel(String(c.concentration))}</Text>
        </View>
      ) : null}

      <Text style={s.footer}>Auto-DM · D&D 5e (2024) character sheet · 2 of 2</Text>
    </Page>
  );
}
