import type { Character } from "../../types";
import {
  formatMod,
  initiativeMod,
  passivePerception,
  proficiencyBonus,
  saveBonus,
  skillBonus,
  spellAttackBonus,
  spellAbility,
  spellSaveDc,
  abilityMod,
} from "./sheetUtils";

const ABILITIES = ["str", "dex", "con", "int", "wis", "cha"] as const;
const SKILLS: { id: string; ability: string; label: string }[] = [
  { id: "acrobatics", ability: "dex", label: "Acrobatics" },
  { id: "animal_handling", ability: "wis", label: "Animal Handling" },
  { id: "arcana", ability: "int", label: "Arcana" },
  { id: "athletics", ability: "str", label: "Athletics" },
  { id: "deception", ability: "cha", label: "Deception" },
  { id: "history", ability: "int", label: "History" },
  { id: "insight", ability: "wis", label: "Insight" },
  { id: "intimidation", ability: "cha", label: "Intimidation" },
  { id: "investigation", ability: "int", label: "Investigation" },
  { id: "medicine", ability: "wis", label: "Medicine" },
  { id: "nature", ability: "int", label: "Nature" },
  { id: "perception", ability: "wis", label: "Perception" },
  { id: "performance", ability: "cha", label: "Performance" },
  { id: "persuasion", ability: "cha", label: "Persuasion" },
  { id: "religion", ability: "int", label: "Religion" },
  { id: "sleight_of_hand", ability: "dex", label: "Sleight of Hand" },
  { id: "stealth", ability: "dex", label: "Stealth" },
  { id: "survival", ability: "wis", label: "Survival" },
];

function mod(score: number): string {
  return formatMod(abilityMod(score));
}

interface Props {
  character: Character;
  summary?: Record<string, unknown>;
  editable?: boolean;
  onChange?: (patch: Partial<Character>) => void;
  page?: 1 | 2;
}

function Field({
  label,
  value,
  editable,
  onChange,
  className = "",
}: {
  label: string;
  value: string;
  editable?: boolean;
  onChange?: (v: string) => void;
  className?: string;
}) {
  return (
    <div className={`sheet-box p-1 ${className}`}>
      <div className="text-[9px] uppercase tracking-wide text-gray-600 font-sans">{label}</div>
      {editable && onChange ? (
        <input
          className="w-full bg-transparent border-none text-sm font-semibold focus:outline-none"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <div className="text-sm font-semibold min-h-[1.25rem]">{value || "—"}</div>
      )}
    </div>
  );
}

function DeathSaves({ successes, failures }: { successes: number; failures: number }) {
  return (
    <div className="sheet-box p-1">
      <div className="text-[9px] uppercase text-gray-600 font-sans mb-1">Death Saves</div>
      <div className="flex gap-3 text-[10px]">
        <div>
          <span className="text-gray-600">Succ </span>
          {[0, 1, 2].map((i) => (
            <span key={i} className={i < successes ? "text-green-700" : "text-gray-400"}>
              {i < successes ? "●" : "○"}
            </span>
          ))}
        </div>
        <div>
          <span className="text-gray-600">Fail </span>
          {[0, 1, 2].map((i) => (
            <span key={i} className={i < failures ? "text-red-700" : "text-gray-400"}>
              {i < failures ? "●" : "○"}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function CharacterSheetView({ character, summary, editable, onChange, page }: Props) {
  const c = character;
  const scores = c.ability_scores || {};
  const profs = new Set(c.skill_proficiencies || []);
  const saves = new Set(c.save_proficiencies || []);
  const pb = proficiencyBonus(c.level || 1);
  const spellAb = spellAbility(c.class_name || "");
  const spellDc = spellSaveDc(c);
  const spellAtk = spellAttackBonus(c);
  const hitDiceMax = Number(c.hit_dice_max ?? c.level ?? 1);
  const hitDiceSpent = Number(c.hit_dice_spent ?? 0);
  const attuned = (c.attuned_items as string[] | undefined) || [];

  const patch = (p: Partial<Character>) => onChange?.({ ...c, ...p });

  const page1 = (
    <div className="grid grid-cols-12 gap-1 p-2 bg-gray-100 text-black font-sheet min-w-[800px]">
      <div className="col-span-4">
        <Field label="Character Name" value={c.name || ""} editable={editable} onChange={(v) => patch({ name: v })} />
      </div>
      <div className="col-span-2">
        <Field label="Background" value={c.background || ""} editable={editable} onChange={(v) => patch({ background: v })} />
      </div>
      <div className="col-span-2">
        <Field
          label="Class"
          value={
            (c.classes?.length
              ? c.classes
              : [{ class_name: c.class_name, level: c.level, subclass: c.subclass }])
              .map((e) =>
                `${e.class_name} ${e.level}${e.subclass ? ` (${e.subclass})` : ""}`,
              )
              .join(" / ") || c.class_name || ""
          }
        />
      </div>
      <div className="col-span-2">
        <Field label="Species" value={c.species || ""} editable={editable} onChange={(v) => patch({ species: v })} />
      </div>
      <div className="col-span-1">
        <Field label="Level" value={String(c.level || 1)} editable={editable} onChange={(v) => patch({ level: parseInt(v) || 1 })} />
      </div>
      <div className="col-span-1">
        <Field label="XP" value={String(c.xp || 0)} editable={editable} onChange={(v) => patch({ xp: parseInt(v) || 0 })} />
      </div>

      <div className="col-span-3 space-y-1">
        {ABILITIES.map((ab) => (
          <div key={ab} className="sheet-box flex items-center gap-2 p-1">
            <span className="uppercase font-bold w-8">{ab}</span>
            <span className="text-lg font-bold">{scores[ab] ?? 10}</span>
            <span className="text-sm">{mod(scores[ab] ?? 10)}</span>
            <span className="text-[9px] ml-auto text-gray-600">Save {saveBonus(c, ab)}</span>
          </div>
        ))}
        <div className="sheet-box p-1 text-center">
          <div className="text-[9px] uppercase text-gray-600 font-sans">Proficiency</div>
          <div className="text-lg font-bold">{formatMod(pb)}</div>
        </div>
      </div>

      <div className="col-span-5 sheet-box p-1">
        <div className="text-[9px] uppercase text-gray-600 font-sans mb-1">Skills</div>
        <div className="grid grid-cols-2 gap-0.5 text-[10px]">
          {SKILLS.map((sk) => (
            <div key={sk.id} className={profs.has(sk.id) ? "font-bold" : "text-gray-600"}>
              {profs.has(sk.id) ? "●" : "○"} {sk.label} {skillBonus(c, sk.id, sk.ability)}
            </div>
          ))}
        </div>
        <div className="mt-1 pt-1 border-t border-gray-300 text-[10px]">
          Passive Perception <span className="font-bold">{passivePerception(c)}</span>
        </div>
      </div>

      <div className="col-span-4 space-y-1">
        <div className="grid grid-cols-3 gap-1">
          <Field label="Armor Class" value={String(c.ac ?? 10)} />
          <Field label="Initiative" value={formatMod(initiativeMod(c))} />
          <Field label="Speed" value={`${c.speed ?? 30} ft`} />
        </div>
        <div className="grid grid-cols-2 gap-1">
          <Field
            label="Hit Points"
            value={`${c.hp ?? 0} / ${c.max_hp ?? 0}`}
            editable={editable}
            onChange={(v) => {
              const [cur, max] = v.split("/").map((s) => parseInt(s.trim()) || 0);
              patch({ hp: cur, max_hp: max || c.max_hp });
            }}
          />
          <Field label="Hit Dice" value={`${hitDiceMax - hitDiceSpent}d${c.hit_die ?? 8}`} />
        </div>
        <DeathSaves
          successes={Number(c.death_save_successes ?? 0)}
          failures={Number(c.death_save_failures ?? 0)}
        />
        <div className="sheet-box p-1 flex items-center gap-2">
          <span className="text-[9px] uppercase text-gray-600 font-sans">Heroic Inspiration</span>
          <span className="text-lg">{c.heroic_inspiration ? "★" : "☆"}</span>
        </div>
        <Field label="Subclass" value={c.subclass || ""} editable={editable} onChange={(v) => patch({ subclass: v })} />
        {spellDc !== null && (
          <div className="grid grid-cols-2 gap-1">
            <Field label="Spell Save DC" value={String(spellDc)} />
            <Field label="Spell Attack" value={formatMod(spellAtk ?? 0)} />
            <Field label="Spellcasting" value={spellAb?.toUpperCase() || ""} className="col-span-2" />
          </div>
        )}
        <Field label="Cantrips" value={(c.cantrips || []).join(", ")} />
        <Field label="Class Features / Feats" value={[c.origin_feat, ...(c.feats || [])].filter(Boolean).join("; ")} />
        <Field label="Weapons" value={(c.weapons || []).map((w) => w.name).join(", ") || "—"} />
      </div>
    </div>
  );

  const spellSlotsMax = (summary?.spell_slots_max as Record<string, number> | undefined) || {};
  const wildShapeMax = Number(summary?.wild_shape_max ?? 0);
  const showWildShape = wildShapeMax > 0 || (c.wild_shape_uses ?? 0) > 0;

  const page2 = (
    <div className="grid grid-cols-12 gap-1 p-2 bg-gray-100 text-black font-sheet min-w-[800px] mt-2">
      <div className="col-span-4 sheet-box p-1">
        <div className="text-[9px] uppercase text-gray-600 font-sans">Spell Slots</div>
        <div className="flex flex-wrap gap-2 mt-1 text-sm">
          {Object.entries(c.spell_slots || {}).length === 0 && <span className="text-gray-500">—</span>}
          {Object.entries(c.spell_slots || {}).map(([lvl, n]) => {
            const max = spellSlotsMax[lvl];
            const label = max != null && max > 0 ? `L${lvl}: ${n}/${max}` : `L${lvl}: ${n}`;
            return <span key={lvl}>{label}</span>;
          })}
        </div>
        {showWildShape && (
          <div className="mt-2 text-[10px]">
            Wild Shape:{" "}
            <span className="font-semibold">
              {c.wild_shape_uses ?? 0}
              {wildShapeMax > 0 ? `/${wildShapeMax}` : ""} remaining
            </span>
          </div>
        )}
        {c.concentration && (
          <div className="mt-2 text-[10px]">
            Concentration: <span className="font-semibold">{String(c.concentration)}</span>
          </div>
        )}
      </div>
      <div className="col-span-8 sheet-box p-1">
        <div className="text-[9px] uppercase text-gray-600 font-sans">Prepared / Known Spells</div>
        <div className="text-sm mt-1">{(c.prepared_spells?.length ? c.prepared_spells : c.known_spells || []).join(", ") || "—"}</div>
      </div>

      <div className="col-span-6 sheet-box p-1 min-h-[80px]">
        <div className="text-[9px] uppercase text-gray-600 font-sans">Equipment</div>
        <div className="text-sm">{(c.inventory || []).join(", ") || "—"}</div>
      </div>
      <div className="col-span-3 sheet-box p-1">
        <div className="text-[9px] uppercase text-gray-600 font-sans">Attuned (max 3)</div>
        <div className="text-sm">{(attuned.length ? attuned : ["—", "—", "—"]).slice(0, 3).join(", ")}</div>
      </div>
      <div className="col-span-3 sheet-box p-1">
        <div className="text-[9px] uppercase text-gray-600 font-sans">Coins</div>
        <div className="text-sm">
          {["cp", "sp", "ep", "gp", "pp"].map((k) => `${c.currency?.[k] || 0}${k.toUpperCase()}`).join(" ")}
        </div>
      </div>

      <div className="col-span-4 sheet-box p-1">
        <Field label="Languages" value={(c.languages as string[] | undefined)?.join(", ") || "Common"} />
        <Field label="Tool Proficiencies" value={(c.tool_proficiencies as string[] | undefined)?.join(", ") || "—"} />
      </div>
      <div className="col-span-4 sheet-box p-1">
        <Field label="Alignment" value={c.alignment || ""} editable={editable} onChange={(v) => patch({ alignment: v })} />
        <Field label="Size" value={String(c.size || "medium")} />
      </div>
      <div className="col-span-4 sheet-box p-1 min-h-[60px]">
        <Field
          label="Appearance / Notes"
          value={String(c.appearance || c.equipment_notes || "")}
          editable={editable}
          onChange={(v) => patch({ appearance: v })}
        />
      </div>

      {(c.conditions as string[] | undefined)?.length ? (
        <div className="col-span-12 sheet-box p-1">
          <div className="text-[9px] uppercase text-gray-600 font-sans">Conditions</div>
          <div className="text-sm">{(c.conditions as string[]).join(", ")}</div>
        </div>
      ) : null}
    </div>
  );

  if (page === 1) return page1;
  if (page === 2) return page2;
  return (
    <div className="overflow-x-auto">
      {page1}
      {page2}
    </div>
  );
}

export { ABILITIES, SKILLS, mod };
