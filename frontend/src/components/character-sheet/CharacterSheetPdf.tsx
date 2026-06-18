import { Document, Page, Text, View, StyleSheet, pdf } from "@react-pdf/renderer";
import type { Character } from "../../types";
import {
  formatMod,
  initiativeMod,
  passivePerception,
  proficiencyBonus,
  spellAttackBonus,
  spellSaveDc,
  abilityMod,
} from "./sheetUtils";

const styles = StyleSheet.create({
  page: { padding: 24, fontSize: 9, fontFamily: "Helvetica" },
  title: { fontSize: 14, marginBottom: 8, fontWeight: "bold" },
  row: { flexDirection: "row", marginBottom: 3 },
  label: { width: 90, color: "#666", fontSize: 8 },
  value: { flex: 1 },
  section: { marginTop: 10, borderTop: "1pt solid #ccc", paddingTop: 6 },
  sectionTitle: { fontSize: 10, fontWeight: "bold", marginBottom: 4 },
  twoCol: { flexDirection: "row", gap: 12 },
  col: { flex: 1 },
});

function SheetDoc({ c }: { c: Character }) {
  const scores = c.ability_scores || {};
  const pb = proficiencyBonus(c.level || 1);
  const spellDc = spellSaveDc(c);
  const spellAtk = spellAttackBonus(c);
  const hitDiceMax = Number(c.hit_dice_max ?? c.level ?? 1);
  const hitDiceSpent = Number(c.hit_dice_spent ?? 0);

  return (
    <Document>
      <Page size="LETTER" style={styles.page}>
        <Text style={styles.title}>{c.name || "Unnamed"} — D&D 5e Character Sheet</Text>
        <View style={styles.row}>
          <Text style={styles.label}>Class</Text>
          <Text style={styles.value}>
            {c.class_name} {c.subclass ? `(${c.subclass})` : ""} — Level {c.level}
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Species / BG</Text>
          <Text style={styles.value}>{c.species} · {c.background}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Alignment</Text>
          <Text style={styles.value}>{c.alignment || "—"}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Abilities (mod / save)</Text>
          <Text>
            STR {scores.str} ({formatMod(abilityMod(scores.str ?? 10))}) · DEX {scores.dex} · CON {scores.con} · INT {scores.int} · WIS {scores.wis} · CHA {scores.cha}
          </Text>
          <Text>Proficiency bonus: {formatMod(pb)} · Passive Perception: {passivePerception(c)}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Combat</Text>
          <Text>AC {c.ac} · HP {c.hp}/{c.max_hp} · Initiative {formatMod(initiativeMod(c))} · Speed {c.speed ?? 30} ft</Text>
          <Text>Hit Dice: {hitDiceMax - hitDiceSpent}d{c.hit_die ?? 8} remaining</Text>
          <Text>
            Death Saves: {c.death_save_successes ?? 0} successes, {c.death_save_failures ?? 0} failures
          </Text>
          {c.heroic_inspiration ? <Text>Heroic Inspiration: yes</Text> : null}
          {spellDc !== null && (
            <Text>Spell Save DC {spellDc} · Spell Attack {formatMod(spellAtk ?? 0)}</Text>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Skills & Saves</Text>
          <Text>Skill proficiencies: {(c.skill_proficiencies || []).join(", ") || "—"}</Text>
          <Text>Save proficiencies: {(c.save_proficiencies || []).join(", ") || "—"}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Features & Feats</Text>
          <Text>{[c.origin_feat, ...(c.feats || [])].filter(Boolean).join("; ") || "—"}</Text>
        </View>
      </Page>

      <Page size="LETTER" style={styles.page}>
        <Text style={styles.title}>Spells & Equipment</Text>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Cantrips & Spells</Text>
          <Text>Cantrips: {(c.cantrips || []).join(", ") || "—"}</Text>
          <Text>Prepared/Known: {(c.prepared_spells?.length ? c.prepared_spells : c.known_spells || []).join(", ") || "—"}</Text>
          <Text>
            Spell slots:{" "}
            {Object.entries(c.spell_slots || {}).map(([l, n]) => `L${l}:${n}`).join(" ") || "—"}
          </Text>
          {c.concentration ? <Text>Concentration: {String(c.concentration)}</Text> : null}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Gear</Text>
          <Text>Weapons: {(c.weapons || []).map((w) => w.name).join(", ") || "—"}</Text>
          <Text>Inventory: {(c.inventory || []).join(", ") || "—"}</Text>
          <Text>
            Coins: {["cp", "sp", "ep", "gp", "pp"].map((k) => `${c.currency?.[k] || 0} ${k.toUpperCase()}`).join(" · ")}
          </Text>
          <Text>Languages: {(c.languages as string[] | undefined)?.join(", ") || "Common"}</Text>
          <Text>Tools: {(c.tool_proficiencies as string[] | undefined)?.join(", ") || "—"}</Text>
        </View>

        {(c.appearance || c.equipment_notes) && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Appearance / Notes</Text>
            <Text>{String(c.appearance || c.equipment_notes)}</Text>
          </View>
        )}
      </Page>
    </Document>
  );
}

export async function downloadCharacterPdf(character: Character, filename?: string) {
  const blob = await pdf(<SheetDoc c={character} />).toBlob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `${character.name || "character"}-sheet.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}
