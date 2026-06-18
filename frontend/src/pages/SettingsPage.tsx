import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function SettingsPage() {
  const [settings, setSettings] = useState({ include_faerun: false, use_rerank: true });
  const [health, setHealth] = useState<{ indexed: boolean; claude_configured: boolean } | null>(null);
  const [indexing, setIndexing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getSettings().then((r) => setSettings(r.settings));
    api.health().then(setHealth);
  }, []);

  const save = async () => {
    const r = await api.updateSettings(settings);
    setSettings(r.settings);
    setMessage("Settings saved.");
  };

  const reindex = async (includeFaerun: boolean) => {
    setIndexing(true);
    setMessage(null);
    try {
      const r = await api.reindex(includeFaerun);
      setMessage(r.ok ? `Indexed ${r.chunk_count} chunks.` : "Indexing failed.");
      const h = await api.health();
      setHealth(h);
    } finally {
      setIndexing(false);
    }
  };

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {health && (
        <div className="panel p-4 text-sm space-y-1">
          <p>Rules index: {health.indexed ? "ready" : "not indexed"}</p>
          <p>Claude API: {health.claude_configured ? "configured" : "missing key"}</p>
        </div>
      )}

      <div className="panel p-4 space-y-4">
        <h2 className="font-semibold">Rules search</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={settings.include_faerun}
            onChange={(e) => setSettings({ ...settings, include_faerun: e.target.checked })}
          />
          Include Heroes of Faerûn & Adventures in Faerûn in rules search
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={settings.use_rerank}
            onChange={(e) => setSettings({ ...settings, use_rerank: e.target.checked })}
          />
          Use cross-encoder reranking (Quality+)
        </label>
        <button type="button" className="btn-primary" onClick={save}>Save settings</button>
      </div>

      <div className="panel p-4 space-y-3">
        <h2 className="font-semibold">Index rulebooks</h2>
        <p className="text-sm text-muted">Requires Ollama with nomic-embed-text. First run may take hours with OCR.</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-ghost" disabled={indexing} onClick={() => reindex(false)}>
            Index core (PHB, DMG, MM)
          </button>
          <button type="button" className="btn-ghost" disabled={indexing} onClick={() => reindex(true)}>
            Index core + Faerûn
          </button>
        </div>
      </div>

      {message && <p className="text-sm text-accent">{message}</p>}
    </div>
  );
}
