import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { Character } from "../../types";
import {
  spellLimitsFromClass,
  spellListField,
  spellPickLabel,
} from "../../lib/dnd5eCharacterCreation";
import CharacterSheetView from "./CharacterSheetView";

const STEPS = ["Basics", "Origin", "Abilities", "Skills & spells", "Review"] as const;
const ABILITIES = ["str", "dex", "con", "int", "wis", "cha"] as const;

interface Option {
  id: string;
  label: string;
  [key: string]: unknown;
}

interface ClassOption extends Option {
  hit_die?: number;
  spellcasting?: string | null;
  spell_list?: string;
  skill_choices?: number;
  skill_options?: string[] | "any";
  cantrips_by_level?: number[];
  prepared_by_level?: number[];
  spells_known_by_level?: number[];
}

interface Props {
  initial?: Character;
  onSave: (char: Character) => void;
  onCancel?: () => void;
}

export default function CharacterWizard({ initial, onSave, onCancel }: Props) {
  const [step, setStep] = useState(0);
  const [options, setOptions] = useState<Record<string, unknown>>({});
  const [char, setChar] = useState<Character>(
    initial || {
      name: "",
      species: "",
      class_name: "",
      subclass: "",
      background: "",
      alignment: "",
      level: 1,
      xp: 0,
      hp: 0,
      max_hp: 0,
      ac: 10,
      speed: 30,
      hit_die: 8,
      ability_scores: { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 },
      base_ability_scores: {},
      ability_scores_set: false,
      skill_proficiencies: [],
      class_skill_choices: [],
      save_proficiencies: [],
      cantrips: [],
      prepared_spells: [],
      known_spells: [],
      spell_slots: {},
      weapons: [],
      inventory: [],
      currency: {},
      feats: [],
      origin_feat: "",
      campaign_setting: "freeform",
      campaign_notes: "",
      human_skill: "",
    },
  );

  useEffect(() => {
    const includeFaerun = char.campaign_setting === "faerun";
    api.getCharacterOptions(includeFaerun).then(setOptions);
  }, [char.campaign_setting]);

  const patch = (p: Partial<Character>) => setChar((c) => ({ ...c, ...p }));

  const classes = (options.classes || []) as ClassOption[];
  const species = (options.species || []) as Option[];
  const backgrounds = (options.backgrounds || []) as (Option & { source?: string; category?: string })[];
  const phbBackgrounds = backgrounds.filter((b) => b.source !== "faerun");
  const faerunBackgrounds = backgrounds.filter((b) => b.source === "faerun");
  const skills = (options.skills || []) as { id: string; label: string }[];
  const selectedClass = classes.find((c) => c.id === char.class_name);
  const spellLimits = useMemo(
    () => spellLimitsFromClass(selectedClass, char.level || 1),
    [selectedClass, char.level],
  );
  const spellField = spellListField(selectedClass?.spellcasting);
  const spellLists = (options.spell_lists || {}) as Record<string, Record<string, string[]>>;
  const spellList = spellLists[selectedClass?.spell_list || char.class_name || ""] || {};

  const toggleSkill = (id: string) => {
    const max = selectedClass?.skill_choices || 0;
    const current = [...((char.class_skill_choices || []) as string[])];
    const idx = current.indexOf(id);
    if (idx >= 0) current.splice(idx, 1);
    else if (current.length < max) current.push(id);
    patch({ class_skill_choices: current });
  };

  const applyStandardArray = () => {
    const table = (options.standard_array_by_class || {}) as Record<string, Record<string, number>>;
    const scores = table[char.class_name];
    if (!scores) return;
    patch({
      base_ability_scores: scores,
      ability_scores: scores,
      ability_scores_set: true,
    });
  };

  const classSkillOptions =
    selectedClass?.skill_options === "any"
      ? skills
      : skills.filter((s) => (selectedClass?.skill_options as string[] | undefined)?.includes(s.id));

  return (
    <div className="panel p-4 space-y-4">
      <div className="flex gap-2 text-xs text-muted flex-wrap">
        {STEPS.map((s, i) => (
          <span key={s} className={i === step ? "text-accent" : ""}>
            {i + 1}. {s}
          </span>
        ))}
      </div>

      {step === 0 && (
        <div className="grid grid-cols-2 gap-3">
          <label className="block col-span-2">
            <span className="text-sm text-muted">Name</span>
            <input className="input mt-1" value={char.name} onChange={(e) => patch({ name: e.target.value })} />
          </label>
          <label className="block">
            <span className="text-sm text-muted">Class</span>
            <select className="input mt-1" value={char.class_name} onChange={(e) => patch({ class_name: e.target.value })}>
              <option value="">—</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm text-muted">Species</span>
            <select className="input mt-1" value={char.species} onChange={(e) => patch({ species: e.target.value })}>
              <option value="">—</option>
              {species.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </label>
          <label className="block col-span-2">
            <span className="text-sm text-muted">Background</span>
            <select className="input mt-1" value={char.background} onChange={(e) => patch({ background: e.target.value })}>
              <option value="">—</option>
              <optgroup label="Player's Handbook">
                {phbBackgrounds.map((b) => (
                  <option key={b.id} value={b.id}>{b.label}</option>
                ))}
              </optgroup>
              {faerunBackgrounds.length > 0 && (
                <optgroup label="Heroes of Faerûn">
                  {faerunBackgrounds.map((b) => (
                    <option key={b.id} value={b.id}>{b.label}</option>
                  ))}
                </optgroup>
              )}
            </select>
          </label>
        </div>
      )}

      {step === 1 && (
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-sm text-muted">Campaign</span>
            <select
              className="input mt-1"
              value={char.campaign_setting}
              onChange={(e) => {
                const setting = e.target.value;
                const isFaerunBg = faerunBackgrounds.some((b) => b.id === char.background);
                patch({
                  campaign_setting: setting,
                  ...(setting !== "faerun" && isFaerunBg ? { background: "" } : {}),
                });
              }}
            >
              <option value="freeform">Freeform</option>
              <option value="faerun">Faerûn</option>
            </select>
          </label>
          {char.campaign_setting === "faerun" && (
            <p className="col-span-2 text-xs text-muted">
              Faerûn backgrounds and subclasses from Heroes of Faerûn are available. Spell and feat details can also be looked up via rules search.
            </p>
          )}
          <label className="block">
            <span className="text-sm text-muted">Alignment</span>
            <input className="input mt-1" value={char.alignment} onChange={(e) => patch({ alignment: e.target.value })} />
          </label>
          <label className="block col-span-2">
            <span className="text-sm text-muted">Campaign notes</span>
            <input className="input mt-1" value={char.campaign_notes} onChange={(e) => patch({ campaign_notes: e.target.value })} />
          </label>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3">
          <button type="button" className="btn-ghost text-xs" onClick={applyStandardArray} disabled={!char.class_name}>
            Apply PHB standard array for class
          </button>
          <div className="grid grid-cols-3 gap-2">
            {ABILITIES.map((ab) => (
              <label key={ab} className="block">
                <span className="text-sm uppercase text-muted">{ab}</span>
                <input
                  type="number"
                  className="input mt-1"
                  value={char.ability_scores[ab] ?? 10}
                  onChange={(e) =>
                    patch({
                      ability_scores: { ...char.ability_scores, [ab]: parseInt(e.target.value) || 10 },
                      base_ability_scores: { ...(char.base_ability_scores || {}), [ab]: parseInt(e.target.value) || 10 },
                      ability_scores_set: true,
                    })
                  }
                />
              </label>
            ))}
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          {selectedClass && (selectedClass.skill_choices || 0) > 0 && (
            <div>
              <p className="text-sm text-muted mb-2">
                Class skills (pick {selectedClass.skill_choices})
              </p>
              <div className="flex flex-wrap gap-2">
                {classSkillOptions.map((sk) => {
                  const picked = ((char.class_skill_choices || []) as string[]).includes(sk.id);
                  return (
                    <button
                      key={sk.id}
                      type="button"
                      className={`btn-ghost text-xs ${picked ? "border-accent" : ""}`}
                      onClick={() => toggleSkill(sk.id)}
                    >
                      {sk.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {selectedClass?.spellcasting && (
            <>
              <label className="block">
                <span className="text-sm text-muted">Cantrips (max {spellLimits.cantrips})</span>
                <select
                  multiple
                  className="input mt-1 h-24"
                  value={char.cantrips}
                  onChange={(e) =>
                    patch({
                      cantrips: Array.from(e.target.selectedOptions, (o) => o.value).slice(0, spellLimits.cantrips),
                    })
                  }
                >
                  {(spellList.cantrips || []).map((sp: string) => (
                    <option key={sp} value={sp}>{sp}</option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-sm text-muted">
                  {spellPickLabel(selectedClass.spellcasting)} (max{" "}
                  {spellLimits[spellField === "known_spells" ? "known" : "prepared"]})
                </span>
                <select
                  multiple
                  className="input mt-1 h-32"
                  value={char[spellField] as string[]}
                  onChange={(e) => {
                    const max = spellLimits[spellField === "known_spells" ? "known" : "prepared"];
                    const picks = Array.from(e.target.selectedOptions, (o) => o.value).slice(0, max);
                    patch({ [spellField]: picks });
                  }}
                >
                  {Object.entries(spellList)
                    .filter(([k]) => k !== "cantrips")
                    .flatMap(([, arr]) => arr as string[])
                    .map((sp: string) => (
                      <option key={sp} value={sp}>{sp}</option>
                    ))}
                </select>
              </label>
            </>
          )}
        </div>
      )}

      {step === 4 && <CharacterSheetView character={char} />}

      <div className="flex gap-2 justify-between">
        <div>{onCancel && <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>}</div>
        <div className="flex gap-2">
          {step > 0 && <button type="button" className="btn-ghost" onClick={() => setStep((s) => s - 1)}>Back</button>}
          {step < STEPS.length - 1 ? (
            <button type="button" className="btn-primary" onClick={() => setStep((s) => s + 1)}>Next</button>
          ) : (
            <button type="button" className="btn-primary" onClick={() => onSave(char)}>Save character</button>
          )}
        </div>
      </div>
    </div>
  );
}
