import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Character, ClassLevel } from "../../types";

interface Props {
  character: Character;
  onChange: (classes: ClassLevel[]) => void;
}

export default function MulticlassPanel({ character, onChange }: Props) {
  const [options, setOptions] = useState<{ id: string; label: string }[]>([]);
  const [addClass, setAddClass] = useState("");
  const [error, setError] = useState<string | null>(null);

  const entries = (character.classes?.length
    ? character.classes
    : character.class_name
      ? [{ class_name: character.class_name, level: character.level, subclass: character.subclass || "" }]
      : []) as ClassLevel[];

  useEffect(() => {
    api.getCharacterOptions(character.campaign_setting === "faerun").then((o) => {
      setOptions((o.classes as { id: string; label: string }[]) || []);
    });
  }, [character.campaign_setting]);

  const existing = new Set(entries.map((e) => e.class_name));
  const available = options.filter((c) => !existing.has(c.id));

  const updateEntry = (idx: number, patch: Partial<ClassLevel>) => {
    const next = entries.map((e, i) => (i === idx ? { ...e, ...patch } : e));
    onChange(next);
  };

  const tryAdd = async () => {
    if (!addClass) return;
    setError(null);
    try {
      if (character.id) {
        const res = await api.addMulticlass(String(character.id), addClass);
        onChange((res.character.classes as ClassLevel[]) || []);
      } else {
        onChange([
          ...entries,
          { class_name: addClass, level: 1, subclass: "", class_skill_choices: [] },
        ]);
      }
      setAddClass("");
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="panel p-4 space-y-3">
      <h3 className="font-semibold text-sm">Multiclass</h3>
      {entries.length === 0 && <p className="text-xs text-muted">Set a primary class first.</p>}
      {entries.map((e, i) => (
        <div key={`${e.class_name}-${i}`} className="grid grid-cols-3 gap-2 text-sm">
          <span className="capitalize">{e.class_name}</span>
          <span>Lv {e.level}</span>
          <input
            className="input text-xs"
            placeholder="Subclass"
            value={e.subclass || ""}
            onChange={(ev) => updateEntry(i, { subclass: ev.target.value })}
          />
        </div>
      ))}
      {character.level < 20 && available.length > 0 && (
        <div className="flex gap-2 items-end">
          <label className="flex-1 block">
            <span className="text-xs text-muted">Add class (level 1)</span>
            <select className="input mt-1" value={addClass} onChange={(ev) => setAddClass(ev.target.value)}>
              <option value="">—</option>
              {available.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </label>
          <button type="button" className="btn-ghost text-xs" disabled={!addClass} onClick={tryAdd}>
            Add
          </button>
        </div>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
      <p className="text-[10px] text-muted">
        Multiclass requires ability score prerequisites (e.g. WIZ INT 13). Level up picks which class gains a level.
      </p>
    </div>
  );
}
