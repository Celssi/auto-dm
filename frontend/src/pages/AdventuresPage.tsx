import { useCallback, useEffect, useState } from "react";
import { api, type AdventureFull } from "../api/client";
import ReactMarkdown from "react-markdown";

export default function AdventuresPage() {
  const [adventures, setAdventures] = useState<{ id: string; name: string; mode: string }[]>([]);
  const [characters, setCharacters] = useState<{ id: string; name: string }[]>([]);
  const [selected, setSelected] = useState<AdventureFull | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "",
    mode: "freeform",
    theme: "",
    character_id: "",
    include_faerun: false,
  });
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [a, c] = await Promise.all([api.listAdventures(), api.listCharacters()]);
    setAdventures(a.adventures);
    setCharacters(c.characters);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [load]);

  const create = async () => {
    setError(null);
    try {
      const res = await api.createAdventure(form);
      setSelected(res.adventure);
      setCreating(false);
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  const open = async (id: string) => {
    const { adventure } = await api.getAdventure(id);
    setSelected(adventure);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Adventures</h1>
        <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
          New adventure
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {creating && (
        <div className="panel p-4 space-y-3">
          <input className="input" placeholder="Adventure name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <select className="input" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}>
            <option value="freeform">Freeform (AI generates)</option>
            <option value="module">Module (from Faerûn books)</option>
            <option value="hybrid">Hybrid</option>
          </select>
          <textarea className="input min-h-[80px]" placeholder="Theme or hook" value={form.theme} onChange={(e) => setForm({ ...form, theme: e.target.value })} />
          <select className="input" value={form.character_id} onChange={(e) => setForm({ ...form, character_id: e.target.value })}>
            <option value="">Character (optional)</option>
            {characters.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.include_faerun} onChange={(e) => setForm({ ...form, include_faerun: e.target.checked })} />
            Include Faerûn supplements in outline generation
          </label>
          <div className="flex gap-2">
            <button type="button" className="btn-primary" onClick={create}>Generate & save</button>
            <button type="button" className="btn-ghost" onClick={() => setCreating(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ul className="panel divide-y divide-border">
          {adventures.map((a) => (
            <li key={a.id}>
              <button type="button" className="w-full text-left p-4 hover:bg-bg/50" onClick={() => open(a.id)}>
                <div className="font-medium">{a.name}</div>
                <div className="text-xs text-muted">{a.mode}</div>
              </button>
            </li>
          ))}
        </ul>

        {selected && (
          <div className="panel p-4 space-y-3 overflow-y-auto max-h-[70vh]">
            <h2 className="font-semibold text-lg">{selected.name}</h2>
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{selected.outline || "_No outline yet._"}</ReactMarkdown>
            </div>
            {selected.log && (
              <>
                <h3 className="text-sm font-semibold text-muted">Adventure log</h3>
                <div className="prose prose-invert prose-sm max-w-none text-xs">
                  <ReactMarkdown>{selected.log}</ReactMarkdown>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
