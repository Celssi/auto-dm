import type { Character } from '../../types';
import { displayLabel, displayLabels, EMPTY_FIELD } from '../../lib/displayText';
import { abilityMod, formatMod, spellAttackBonus, spellAbility, spellSaveDc } from './sheetUtils';
import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';
import { splitNotes } from './characterSheetPdfUtils';
import { createPdfParts } from './characterSheetPdfParts';

export function buildSheetPage2(pdf: PdfModule, c: Character) {
  const { Page, Text, View } = pdf;
  const { Box } = createPdfParts(pdf);
  const spellAb = spellAbility(c.class_name || '');
  const spellDc = spellSaveDc(c);
  const spellAtk = spellAttackBonus(c);
  const spellMod = spellAb ? formatMod(abilityMod(c.ability_scores?.[spellAb] ?? 10)) : EMPTY_FIELD;
  const prepared = c.prepared_spells?.length ? c.prepared_spells : c.known_spells || [];
  const notesText = String(c.appearance || c.equipment_notes || '');
  const { appearance, backstory } = splitNotes(notesText);
  const attuned = (c.attuned_items as string[] | undefined) || [];
  const slots = c.spell_slots || {};

  return (
    <Page size="LETTER" style={s.page}>
      <View style={[s.row, { gap: 4, marginBottom: 4 }]}>
        <View style={[s.box, { width: 110, padding: 4 }]}>
          <Text style={[s.label, { marginBottom: 4 }]}>Spellcasting</Text>
          <View style={[s.row, { justifyContent: 'space-between', marginBottom: 3 }]}>
            <Text style={s.labelSm}>Modifier</Text>
            <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold' }}>{spellMod}</Text>
          </View>
          <View style={[s.row, { justifyContent: 'space-between', marginBottom: 3 }]}>
            <Text style={s.labelSm}>Spell Save DC</Text>
            <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold' }}>{spellDc ?? EMPTY_FIELD}</Text>
          </View>
          <View style={[s.row, { justifyContent: 'space-between' }]}>
            <Text style={s.labelSm}>Spell Attack</Text>
            <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold' }}>
              {spellAtk !== null ? formatMod(spellAtk) : EMPTY_FIELD}
            </Text>
          </View>
          {spellAb ? (
            <Text style={{ fontSize: 12, marginTop: 4, color: '#555' }}>Ability: {spellAb.toUpperCase()}</Text>
          ) : null}
        </View>

        <Box title="Spell Slots" style={{ flex: 1 }}>
          <View style={[s.row, { padding: 4, gap: 2 }]}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((lvl) => {
              const remaining = slots[String(lvl)] ?? 0;
              const max = remaining;
              return (
                <View key={lvl} style={{ flex: 1, alignItems: 'center' }}>
                  <Text style={s.labelSm}>L{lvl}</Text>
                  <Text style={{ fontSize: 12, marginTop: 1 }}>Total</Text>
                  <View style={[s.row, { gap: 1, marginVertical: 1 }]}>
                    {Array.from({ length: Math.max(max, 1) }).map((_, i) => (
                      <Text key={`slot-pip-${lvl}-${i}`} style={{ fontSize: 12 }}>
                        {i < max ? '◆' : '◇'}
                      </Text>
                    ))}
                  </View>
                  <Text style={{ fontSize: 12 }}>Expended</Text>
                  <Text style={{ fontSize: 12 }}>
                    {Math.max(0, max - remaining)}/{max || 0}
                  </Text>
                </View>
              );
            })}
          </View>
        </Box>
      </View>

      <View style={[s.row, { flex: 1, gap: 4 }]}>
        <Box title="Cantrips & Prepared Spells" style={{ flex: 1.55 }}>
          <View style={s.tableHeader}>
            <Text style={[s.labelSm, { width: 24 }]}>Level</Text>
            <Text style={[s.labelSm, { width: '22%' }]}>Name</Text>
            <Text style={[s.labelSm, { width: '14%' }]}>Casting Time</Text>
            <Text style={[s.labelSm, { width: '12%' }]}>Range</Text>
            <Text style={[s.labelSm, { width: '18%' }]}>C / R / M</Text>
            <Text style={[s.labelSm, { flex: 1 }]}>Notes</Text>
          </View>
          {[
            ...(c.cantrips || []).map((n) => ({ name: n, level: 'C' })),
            ...prepared.map((n) => ({ name: n, level: '' })),
          ].map((sp) => (
            <View key={`spell-${sp.name}-${sp.level}`} style={s.tableRow}>
              <Text style={{ width: 24, fontSize: 12 }}>{sp.level}</Text>
              <Text style={{ width: '22%', fontSize: 12 }}>{displayLabel(sp.name)}</Text>
              <Text style={{ width: '14%', fontSize: 12 }}> </Text>
              <Text style={{ width: '12%', fontSize: 12 }}> </Text>
              <Text style={{ width: '18%', fontSize: 12, color: '#888' }}>○ ○ ○</Text>
              <Text style={{ flex: 1, fontSize: 12 }}> </Text>
            </View>
          ))}
          {Array.from({ length: Math.max(0, 22 - prepared.length - (c.cantrips?.length || 0)) }).map((_, i) => (
            <View key={`spell-placeholder-${i}`} style={s.tableRow}>
              <Text style={{ width: 24 }}> </Text>
              <Text style={{ width: '22%' }}> </Text>
              <Text style={{ width: '14%' }}> </Text>
              <Text style={{ width: '12%' }}> </Text>
              <Text style={{ width: '18%' }}> </Text>
              <Text style={{ flex: 1 }}> </Text>
            </View>
          ))}
        </Box>

        <View style={{ width: 168 }}>
          <Box title="Appearance" style={{ marginBottom: 4, minHeight: 72 }}>
            <View style={{ padding: 5, minHeight: 58 }}>
              <Text style={{ fontSize: 12 }}>{appearance || ' '}</Text>
            </View>
          </Box>
          <Box title="Backstory & Personality" style={{ marginBottom: 4, minHeight: 120 }}>
            <View style={[s.gridBg, { padding: 5, minHeight: 90 }]}>
              <Text style={{ fontSize: 12 }}>{backstory || ' '}</Text>
            </View>
            <View style={{ borderTop: '0.5pt solid #000', padding: 4 }}>
              <Text style={s.labelSm}>Alignment</Text>
              <Text style={{ fontSize: 12, marginTop: 1 }}>{c.alignment || ' '}</Text>
            </View>
          </Box>
          <Box title="Languages" style={{ marginBottom: 4, minHeight: 48 }}>
            <View style={[s.gridBg, { padding: 5 }]}>
              <Text style={{ fontSize: 12 }}>
                {displayLabels((c.languages as string[] | undefined) || ['Common'], ', ')}
              </Text>
            </View>
          </Box>
          <Box title="Equipment" style={{ marginBottom: 4, minHeight: 110 }}>
            <View style={[s.gridBg, { padding: 5, minHeight: 70 }]}>
              {(c.inventory || []).map((item) => (
                <Text key={`inv-${item}`} style={{ fontSize: 12, marginBottom: 2 }}>
                  • {displayLabel(item)}
                </Text>
              ))}
            </View>
            <View style={{ borderTop: '0.5pt solid #000', padding: 4 }}>
              <Text style={s.labelSm}>Magic Item Attunement</Text>
              {[0, 1, 2].map((i) => (
                <View key={`attuned-slot-${i}`} style={[s.row, { alignItems: 'center', marginTop: 2 }]}>
                  <Text style={{ fontSize: 12, marginRight: 4 }}>{attuned[i] ? '◆' : '◇'}</Text>
                  <Text style={{ fontSize: 12, flex: 1 }}>{attuned[i] ? displayLabel(attuned[i]) : ' '}</Text>
                </View>
              ))}
            </View>
          </Box>
          <Box title="Coins">
            <View style={[s.row, { padding: 4 }]}>
              {(['cp', 'sp', 'ep', 'gp', 'pp'] as const).map((k) => (
                <View
                  key={k}
                  style={{ flex: 1, alignItems: 'center', borderRight: k !== 'pp' ? '0.5pt solid #ccc' : undefined }}
                >
                  <Text style={s.labelSm}>{k.toUpperCase()}</Text>
                  <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold', marginTop: 2 }}>
                    {c.currency?.[k] || 0}
                  </Text>
                </View>
              ))}
            </View>
          </Box>
        </View>
      </View>

      {c.concentration ? (
        <View style={[s.box, { marginTop: 4, padding: 4 }]}>
          <Text style={s.labelSm}>Concentration</Text>
          <Text style={{ fontSize: 12 }}>{displayLabel(String(c.concentration))}</Text>
        </View>
      ) : null}

      <Text style={s.footer}>Auto-DM · D&D 5e (2024) character sheet · 2 of 2</Text>
    </Page>
  );
}
