import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Character } from "../types";
import CharacterWizard from "../components/character-sheet/CharacterWizard";
import CharacterSheetView from "../components/character-sheet/CharacterSheetView";
import LevelUpDialog from "../components/character-sheet/LevelUpDialog";
import MulticlassPanel from "../components/character-sheet/MulticlassPanel";
import { downloadCharacterPdf } from "../components/character-sheet/CharacterSheetPdf";

export default function CharactersPage() {
  const [roster, setRoster] = useState<{ id: string; name: string }[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [character, setCharacter] = useState<Character | null>(null);
  const [summary, setSummary] = useState<Record<string, unknown>>({});
  const [mode, setMode] = useState<"list" | "wizard" | "view">("list");
  const [levelUpOpen, setLevelUpOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { characters } = await api.listCharacters();
    setRoster(characters);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [load]);

  const openChar = async (id: string) => {
    const [{ character: c }, sum] = await Promise.all([
      api.getCharacter(id),
      api.getCharacterSummary(id),
    ]);
    setCharacter(c as Character);
    setSummary(sum.summary);
    setActiveId(id);
    setMode("view");
  };

  const saveChar = async (c: Character) => {
    let id = activeId;
    if (id) {
      await api.updateCharacter(id, c as Record<string, unknown>);
    } else {
      const res = await api.createCharacter(c as Record<string, unknown>);
      id = res.id;
      setActiveId(res.id);
      setCharacter(res.character as Character);
    }
    await load();
    setMode("view");
    if (id) {
      const sum = await api.getCharacterSummary(id);
      setSummary(sum.summary);
      setCharacter(sum.character as Character);
    }
  };

  const levelUp = async (
    hpRoll: number | undefined,
    asiChoices: Record<string, unknown>[],
    className?: string,
  ) => {
    if (!activeId) return;
    const res = await api.levelUpCharacter(activeId, {
      hp_roll: hpRoll,
      asi_choices: asiChoices,
      class_name: className,
    });
    setCharacter(res.character as Character);
    setSummary(res.summary);
    setLevelUpOpen(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Characters</h1>
        <button
          type="button"
          className="btn-primary"
          onClick={() => {
            setActiveId(null);
            setCharacter(null);
            setMode("wizard");
          }}
        >
          New character
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {mode === "list" && (
        <ul className="panel divide-y divide-border">
          {roster.length === 0 && <li className="p-4 text-muted text-sm">No characters yet.</li>}
          {roster.map((r) => (
            <li key={r.id}>
              <button type="button" className="w-full text-left p-4 hover:bg-bg/50" onClick={() => openChar(r.id)}>
                {r.name}
              </button>
            </li>
          ))}
        </ul>
      )}

      {mode === "wizard" && (
        <CharacterWizard initial={character || undefined} onSave={saveChar} onCancel={() => setMode("list")} />
      )}

      {mode === "view" && character && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-ghost" onClick={() => setMode("list")}>
              Back
            </button>
            <button type="button" className="btn-ghost" onClick={() => setMode("wizard")}>
              Edit
            </button>
            <button type="button" className="btn-primary" onClick={() => setLevelUpOpen(true)}>
              Level up
            </button>
            <button type="button" className="btn-ghost" onClick={() => downloadCharacterPdf(character)}>
              Export PDF
            </button>
          </div>
          {Boolean(summary.needs_asi) && (
            <p className="text-sm text-yellow-400">ASI/Feat choice available before or after leveling.</p>
          )}
          <MulticlassPanel
            character={{ ...character, id: activeId || undefined }}
            onChange={(classes) => setCharacter({ ...character, classes })}
          />
          {summary.unlocked_features ? (
            <div className="panel p-3 text-xs space-y-1">
              <h3 className="font-semibold text-sm">Unlocked features</h3>
              {Object.entries(
                (summary.unlocked_features as { class_features?: Record<string, string[]> }).class_features || {},
              ).map(([cid, feats]) => (
                <p key={cid}><span className="text-muted capitalize">{cid}:</span> {(feats as string[]).join(", ")}</p>
              ))}
              {Object.entries(
                (summary.unlocked_features as { subclass_features?: Record<string, string[]> }).subclass_features || {},
              ).map(([key, feats]) => (
                <p key={key}><span className="text-muted">{key}:</span> {(feats as string[]).join(", ")}</p>
              ))}
            </div>
          ) : null}
          <CharacterSheetView
            character={character}
            summary={summary}
            editable
            onChange={(c) => setCharacter(c as Character)}
          />
          <button type="button" className="btn-primary" onClick={() => saveChar(character)}>
            Save changes
          </button>
        </div>
      )}

      {levelUpOpen && character && (
        <LevelUpDialog
          character={character}
          summary={summary}
          onConfirm={levelUp}
          onCancel={() => setLevelUpOpen(false)}
        />
      )}
    </div>
  );
}
