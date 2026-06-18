import { useState } from "react";
import type { Character, ClassLevel } from "../../types";

interface Summary {
  asi_feat_slots?: number;
  asi_feat_taken?: number;
  needs_asi?: boolean;
  hit_die?: number;
  classes?: ClassLevel[];
  multiclass?: boolean;
}

interface Props {
  character: Character;
  summary: Summary;
  onConfirm: (
    hpRoll: number | undefined,
    asiChoices: Record<string, unknown>[],
    className?: string,
  ) => void;
  onCancel: () => void;
}

const ABILITIES = ["str", "dex", "con", "int", "wis", "cha"] as const;

export default function LevelUpDialog({ character, summary, onConfirm, onCancel }: Props) {
  const classEntries = (summary.classes?.length
    ? summary.classes
    : [{ class_name: character.class_name, level: character.level }]) as ClassLevel[];
  const [targetClass, setTargetClass] = useState(classEntries[0]?.class_name || character.class_name);
  const selected = classEntries.find((c) => c.class_name === targetClass) || classEntries[0];
  const hitDie = summary.hit_die || character.hit_die || 8;
  const [hpMode, setHpMode] = useState<"roll" | "average">("roll");
  const [hpRoll, setHpRoll] = useState<number | "">("");
  const asiChoices = (character.asi_choices || []) as Record<string, unknown>[];
  const [localAsi, setLocalAsi] = useState<Record<string, unknown>[]>(asiChoices);
  const needsAsi = summary.needs_asi;

  const addAsi = () => setLocalAsi([...localAsi, { type: "asi", plus: { str: 2 } }]);
  const addFeat = () => setLocalAsi([...localAsi, { type: "feat", feat: "" }]);

  const confirm = () => {
    const roll = hpMode === "average" ? Math.floor(hitDie / 2) + 1 : hpRoll === "" ? undefined : Number(hpRoll);
    onConfirm(roll, localAsi, targetClass);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="panel p-6 max-w-md w-full space-y-4">
        <h2 className="text-lg font-bold">Level up → total {character.level + 1}</h2>

        {classEntries.length > 1 && (
          <label className="block">
            <span className="text-sm text-muted">Which class?</span>
            <select className="input mt-1" value={targetClass} onChange={(e) => setTargetClass(e.target.value)}>
              {classEntries.map((c) => (
                <option key={c.class_name} value={c.class_name}>
                  {c.class_name} (currently {c.level})
                </option>
              ))}
              {!classEntries.some((c) => c.class_name === targetClass) && (
                <option value={targetClass}>{targetClass} (new level 1)</option>
              )}
            </select>
          </label>
        )}

        <div>
          <p className="text-sm text-muted mb-2">
            Hit Points (d{hitDie} + CON) for {selected?.class_name || character.class_name}
          </p>
          <div className="flex gap-2 mb-2">
            <button type="button" className={`btn-ghost text-xs ${hpMode === "roll" ? "border-accent" : ""}`} onClick={() => setHpMode("roll")}>
              Roll
            </button>
            <button type="button" className={`btn-ghost text-xs ${hpMode === "average" ? "border-accent" : ""}`} onClick={() => setHpMode("average")}>
              Average ({Math.floor(hitDie / 2) + 1})
            </button>
          </div>
          {hpMode === "roll" && (
            <input
              type="number"
              className="input"
              min={1}
              max={hitDie}
              placeholder={`1–${hitDie}`}
              value={hpRoll}
              onChange={(e) => setHpRoll(e.target.value === "" ? "" : parseInt(e.target.value))}
            />
          )}
        </div>

        {needsAsi && (
          <div>
            <p className="text-sm text-muted mb-2">
              ASI / Feat ({summary.asi_feat_taken}/{summary.asi_feat_slots} taken)
            </p>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {localAsi.map((choice, i) => (
                <div key={i} className="text-xs border border-border rounded p-2">
                  {choice.type === "feat" ? (
                    <input
                      className="input text-xs"
                      placeholder="Feat name"
                      value={String(choice.feat || "")}
                      onChange={(e) => {
                        const next = [...localAsi];
                        next[i] = { ...choice, feat: e.target.value };
                        setLocalAsi(next);
                      }}
                    />
                  ) : (
                    <div className="flex gap-1 flex-wrap">
                      {ABILITIES.map((ab) => (
                        <select
                          key={ab}
                          className="input text-xs w-16"
                          value={Number((choice.plus as Record<string, number>)?.[ab] || 0)}
                          onChange={(e) => {
                            const next = [...localAsi];
                            const plus = { ...(choice.plus as Record<string, number>) };
                            plus[ab] = parseInt(e.target.value) || 0;
                            next[i] = { ...choice, plus };
                            setLocalAsi(next);
                          }}
                        >
                          <option value={0}>{ab.toUpperCase()}</option>
                          <option value={1}>+1</option>
                          <option value={2}>+2</option>
                        </select>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-2">
              <button type="button" className="btn-ghost text-xs" onClick={addAsi}>+ ASI</button>
              <button type="button" className="btn-ghost text-xs" onClick={addFeat}>+ Feat</button>
            </div>
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
          <button type="button" className="btn-primary" onClick={confirm}>Level up</button>
        </div>
      </div>
    </div>
  );
}
