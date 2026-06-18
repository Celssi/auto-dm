import { useCallback, useEffect, useState } from "react";
import { api, type CampaignFull, type JournalEntry } from "../api/client";

type Tab = "story" | "npcs" | "locations";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<{ id: string; name: string }[]>([]);
  const [selected, setSelected] = useState<CampaignFull | null>(null);
  const [tab, setTab] = useState<Tab>("story");
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", story_arc: "" });

  const load = useCallback(async () => {
    const res = await api.listCampaigns();
    setCampaigns(res.campaigns);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [load]);

  const open = async (id: string) => {
    setEntry(null);
    const { campaign } = await api.getCampaign(id);
    setSelected(campaign);
    setTab("story");
  };

  const create = async () => {
    setError(null);
    try {
      const res = await api.createCampaign(form);
      setSelected(res.campaign);
      setCreating(false);
      setForm({ name: "", story_arc: "" });
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  const openEntry = async (kind: "npc" | "location", id: string) => {
    if (!selected) return;
    if (kind === "npc") {
      const { npc } = await api.getCampaignNpc(selected.id, id);
      setEntry(npc);
    } else {
      const { location } = await api.getCampaignLocation(selected.id, id);
      setEntry(location);
    }
  };

  const saveEntry = async () => {
    if (!selected || !entry) return;
    if (tab === "npcs") {
      await api.updateCampaignNpc(selected.id, entry.id, { name: entry.name, body: entry.body });
    } else if (tab === "locations") {
      await api.updateCampaignLocation(selected.id, entry.id, { name: entry.name, body: entry.body });
    }
    await open(selected.id);
    setEntry(null);
  };

  const list = tab === "npcs" ? selected?.npcs : tab === "locations" ? selected?.locations : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Campaigns</h1>
        <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
          New campaign
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {creating && (
        <div className="panel p-4 space-y-3">
          <input
            className="input"
            placeholder="Campaign name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <textarea
            className="input min-h-[120px]"
            placeholder="Story arc / campaign notes"
            value={form.story_arc}
            onChange={(e) => setForm({ ...form, story_arc: e.target.value })}
          />
          <div className="flex gap-2">
            <button type="button" className="btn-primary" onClick={create}>
              Create
            </button>
            <button type="button" className="btn-ghost" onClick={() => setCreating(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ul className="panel divide-y divide-border">
          {campaigns.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className="w-full text-left p-4 hover:bg-bg/50"
                onClick={() => open(c.id)}
              >
                <div className="font-medium">{c.name}</div>
                <div className="text-xs text-muted">{c.id}</div>
              </button>
            </li>
          ))}
        </ul>

        {selected && (
          <div className="lg:col-span-2 panel p-4 space-y-4">
            <h2 className="font-semibold text-lg">{selected.name}</h2>
            <div className="flex gap-2 text-sm">
              {(["story", "npcs", "locations"] as Tab[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  className={tab === t ? "btn-primary text-xs px-3 py-1" : "btn-ghost text-xs px-3 py-1"}
                  onClick={() => {
                    setTab(t);
                    setEntry(null);
                  }}
                >
                  {t === "story" ? "Story arc" : t === "npcs" ? `NPCs (${selected.npcs?.length ?? 0})` : `Locations (${selected.locations?.length ?? 0})`}
                </button>
              ))}
            </div>

            {tab === "story" && (
              <pre className="text-sm whitespace-pre-wrap text-muted max-h-[60vh] overflow-y-auto">
                {selected.story_arc || "_No story arc yet._"}
              </pre>
            )}

            {tab !== "story" && !entry && (
              <ul className="divide-y divide-border max-h-[50vh] overflow-y-auto">
                {(list || []).map((row) => (
                  <li key={row.id}>
                    <button
                      type="button"
                      className="w-full text-left py-2 hover:text-accent"
                      onClick={() => openEntry(tab === "npcs" ? "npc" : "location", row.id)}
                    >
                      {row.name}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {entry && (
              <div className="space-y-3">
                <input
                  className="input"
                  value={entry.name}
                  onChange={(e) => setEntry({ ...entry, name: e.target.value })}
                />
                <textarea
                  className="input min-h-[280px] font-mono text-sm"
                  value={entry.body}
                  onChange={(e) => setEntry({ ...entry, body: e.target.value })}
                />
                <div className="flex gap-2">
                  <button type="button" className="btn-primary" onClick={saveEntry}>
                    Save
                  </button>
                  <button type="button" className="btn-ghost" onClick={() => setEntry(null)}>
                    Back
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
