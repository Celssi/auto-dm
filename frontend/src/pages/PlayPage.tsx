import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api, type ChatResult, type Shortcut, type Source, type SpellConfirmation } from "../api/client";
import type { Character } from "../types";
import CharacterSheetView from "../components/character-sheet/CharacterSheetView";

type PlayMode = "freeform" | "module";

export default function PlayPage() {
  const { sessionId: paramId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<{ id: string; name: string }[]>([]);
  const [characters, setCharacters] = useState<{ id: string; name: string }[]>([]);
  const [adventures, setAdventures] = useState<{ id: string; name: string }[]>([]);
  const [sessionId, setSessionId] = useState(paramId || "");
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [character, setCharacter] = useState<Character | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [bootstrapError, setBootstrapError] = useState("");
  const [shortcuts, setShortcuts] = useState<Shortcut[]>([]);
  const [oracles, setOracles] = useState<{ id: string; label: string }[]>([]);
  const [lonelog, setLonelog] = useState<string[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [includeFaerun, setIncludeFaerun] = useState(false);
  const [wizardTab, setWizardTab] = useState<"continue" | "new">(
    searchParams.get("new") === "1" ? "new" : "continue",
  );
  const [newSession, setNewSession] = useState({ character_id: "", adventure_id: "", name: "" });
  const [newCampaign, setNewCampaign] = useState({
    character_id: "",
    mode: "freeform" as PlayMode,
    theme: "",
    campaign_name: "",
    include_faerun: false,
  });
  const [spellConfirm, setSpellConfirm] = useState<SpellConfirmation | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadMeta = useCallback(async () => {
    const [s, c, a, sh, or] = await Promise.all([
      api.listSessions(),
      api.listCharacters(),
      api.listAdventures(),
      api.getShortcuts(),
      api.getOracles(),
    ]);
    setSessions(s.sessions);
    setCharacters(c.characters);
    setAdventures(a.adventures);
    setShortcuts(sh.shortcuts);
    setOracles(or.oracles);
    if (s.sessions.length === 0) {
      setWizardTab("new");
    }
  }, []);

  const loadSession = useCallback(async (id: string) => {
    const { session } = await api.getSession(id);
    setMessages(session.messages || []);
    setIncludeFaerun(!!session.include_faerun);
    const { character: ch } = await api.getCharacter(session.character_id);
    setCharacter(ch as Character);
    const log = await api.getLonelog(id);
    setLonelog(log.lines);
  }, []);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  useEffect(() => {
    if (paramId) {
      setSessionId(paramId);
      loadSession(paramId);
    }
  }, [paramId, loadSession]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startSession = async () => {
    const res = await api.createSession({
      ...newSession,
      include_faerun: includeFaerun,
    });
    setSessionId(res.id);
    navigate(`/play/${res.id}`);
    await loadSession(res.id);
    await loadMeta();
  };

  const bootstrapAndPlay = async () => {
    if (!newCampaign.character_id || !newCampaign.theme.trim()) return;
    setBootstrapError("");
    setBootstrapping(true);
    try {
      const result = await api.bootstrapCampaign({
        character_id: newCampaign.character_id,
        mode: newCampaign.mode,
        theme: newCampaign.theme.trim(),
        include_faerun: newCampaign.include_faerun,
        campaign_name: newCampaign.campaign_name.trim(),
      });
      setSessionId(result.session_id);
      navigate(`/play/${result.session_id}`);
      await loadSession(result.session_id);
      await loadMeta();
    } catch (e) {
      setBootstrapError(e instanceof Error ? e.message : "Bootstrap failed");
    } finally {
      setBootstrapping(false);
    }
  };

  const sendMessage = async (msg: string) => {
    if (!sessionId || !msg.trim() || loading) return;
    const text = msg.trim();
    setInput("");
    setSpellConfirm(null);
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const result: ChatResult = await api.chat(sessionId, text);
      setMessages((m) => [...m, { role: "assistant", content: result.response }]);
      setCharacter(result.character as Character);
      setSources(result.sources || []);
      setSpellConfirm(result.spell_confirmation ?? null);
      const log = await api.getLonelog(sessionId);
      setLonelog(log.lines);
    } finally {
      setLoading(false);
    }
  };

  const send = async () => {
    await sendMessage(input);
  };

  const confirmSpellCast = () => {
    if (spellConfirm) sendMessage("yes");
  };

  const cancelSpellCast = () => {
    sendMessage("cancel spell");
  };

  const runOracle = async (id: string) => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const result = await api.runOracle(sessionId, id);
      setMessages((m) => [
        ...m,
        { role: "user", content: `[oracle: ${id}]` },
        { role: "assistant", content: String(result.summary) },
      ]);
      const log = await api.getLonelog(sessionId);
      setLonelog(log.lines);
    } finally {
      setLoading(false);
    }
  };

  const runShortcut = async (id: string) => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const result = await api.runShortcut(sessionId, id);
      const text = String(result.user_message || result.summary || "Shortcut executed.");
      setMessages((m) => [...m, { role: "user", content: `[${id}]` }, { role: "assistant", content: text }]);
    } finally {
      setLoading(false);
    }
  };

  if (!sessionId) {
    return (
      <div className="max-w-lg mx-auto panel p-6 space-y-4">
        <h1 className="text-2xl font-bold">Play</h1>

        <div className="flex gap-2 border-b border-border pb-2">
          <button
            type="button"
            className={`text-sm px-3 py-1 rounded ${wizardTab === "continue" ? "bg-accent/20 text-accent" : "text-muted"}`}
            onClick={() => setWizardTab("continue")}
          >
            Continue
          </button>
          <button
            type="button"
            className={`text-sm px-3 py-1 rounded ${wizardTab === "new" ? "bg-accent/20 text-accent" : "text-muted"}`}
            onClick={() => setWizardTab("new")}
          >
            New campaign
          </button>
        </div>

        {wizardTab === "continue" && (
          <div className="space-y-4">
            {sessions.length > 0 ? (
              <div className="space-y-1">
                <p className="text-sm text-muted">Recent sessions</p>
                {sessions.slice(0, 8).map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className="block w-full text-left py-2 text-sm hover:text-accent border-b border-border/50"
                    onClick={() => navigate(`/play/${s.id}`)}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted">No sessions yet. Start a new campaign below.</p>
            )}

            <details className="text-sm">
              <summary className="cursor-pointer text-muted hover:text-accent">Advanced: link existing adventure</summary>
              <div className="mt-3 space-y-3 pl-2 border-l border-border">
                <select
                  className="input"
                  value={newSession.character_id}
                  onChange={(e) => setNewSession({ ...newSession, character_id: e.target.value })}
                >
                  <option value="">Select character</option>
                  {characters.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <select
                  className="input"
                  value={newSession.adventure_id}
                  onChange={(e) => setNewSession({ ...newSession, adventure_id: e.target.value })}
                >
                  <option value="">Select adventure</option>
                  {adventures.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
                <input
                  className="input"
                  placeholder="Session name (optional)"
                  value={newSession.name}
                  onChange={(e) => setNewSession({ ...newSession, name: e.target.value })}
                />
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={includeFaerun} onChange={(e) => setIncludeFaerun(e.target.checked)} />
                  Include Faerûn supplements in rules search
                </label>
                <button
                  type="button"
                  className="btn-primary w-full"
                  disabled={!newSession.character_id || !newSession.adventure_id}
                  onClick={startSession}
                >
                  Begin play
                </button>
              </div>
            </details>
          </div>
        )}

        {wizardTab === "new" && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Generate a campaign, adventure, journal entries, and opening scene — then jump straight into play.
            </p>

            <select
              className="input"
              value={newCampaign.character_id}
              onChange={(e) => setNewCampaign({ ...newCampaign, character_id: e.target.value })}
            >
              <option value="">Select character</option>
              {characters.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            {characters.length === 0 && (
              <p className="text-xs text-muted">
                <Link to="/characters" className="text-accent hover:underline">Create a character</Link> first.
              </p>
            )}

            <div className="flex gap-2">
              <button
                type="button"
                className={`flex-1 text-sm py-2 rounded border ${newCampaign.mode === "freeform" ? "border-accent bg-accent/10" : "border-border"}`}
                onClick={() => setNewCampaign({ ...newCampaign, mode: "freeform" })}
              >
                Freeform
              </button>
              <button
                type="button"
                className={`flex-1 text-sm py-2 rounded border ${newCampaign.mode === "module" ? "border-accent bg-accent/10" : "border-border"}`}
                onClick={() => setNewCampaign({ ...newCampaign, mode: "module" })}
              >
                Module (RAG)
              </button>
            </div>

            <textarea
              className="input min-h-[80px]"
              placeholder="Theme / hook (e.g. A haunted mine near Waterdeep)"
              value={newCampaign.theme}
              onChange={(e) => setNewCampaign({ ...newCampaign, theme: e.target.value })}
            />

            <input
              className="input"
              placeholder="Campaign name (optional)"
              value={newCampaign.campaign_name}
              onChange={(e) => setNewCampaign({ ...newCampaign, campaign_name: e.target.value })}
            />

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={newCampaign.include_faerun}
                onChange={(e) => setNewCampaign({ ...newCampaign, include_faerun: e.target.checked })}
              />
              Use Faerûn supplements (Heroes & Adventures)
            </label>

            {bootstrapError && <p className="text-sm text-red-400">{bootstrapError}</p>}

            <button
              type="button"
              className="btn-primary w-full"
              disabled={!newCampaign.character_id || !newCampaign.theme.trim() || bootstrapping}
              onClick={bootstrapAndPlay}
            >
              {bootstrapping ? "Generating campaign… (30–60 s)" : "Generate & play"}
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[calc(100vh-8rem)]">
      <aside className="lg:col-span-3 panel overflow-y-auto p-3 space-y-2">
        <h2 className="text-sm font-semibold text-muted">Character</h2>
        {character && <CharacterSheetView character={character} page={1} />}
      </aside>

      <main className="lg:col-span-6 panel flex flex-col min-h-0">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "text-right" : ""}>
              <div className={`inline-block max-w-[90%] rounded-lg px-3 py-2 text-sm ${m.role === "user" ? "bg-accent/20" : "bg-bg"}`}>
                <ReactMarkdown>{m.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {loading && <p className="text-muted text-sm animate-pulse">DM is thinking…</p>}
          <div ref={bottomRef} />
        </div>
        <div className="border-t border-border p-3 space-y-2">
          {spellConfirm && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm">
              <p className="text-muted mb-2">
                Cast <span className="font-semibold text-foreground">{spellConfirm.suggested}</span>
                {" "}(you wrote “{spellConfirm.requested}”)?
              </p>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="btn-primary text-xs" onClick={confirmSpellCast} disabled={loading}>
                  Cast {spellConfirm.suggested}
                </button>
                <button type="button" className="btn-ghost text-xs" onClick={cancelSpellCast} disabled={loading}>
                  No, narrative only
                </button>
              </div>
            </div>
          )}
          <div className="flex gap-2">
          <input
            className="input flex-1"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="What do you do?"
            disabled={loading}
          />
          <button type="button" className="btn-primary" onClick={send} disabled={loading}>
            Send
          </button>
          </div>
        </div>
      </main>

      <aside className="lg:col-span-3 panel overflow-y-auto p-3 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-muted mb-2">Oracles</h2>
          <div className="flex flex-wrap gap-1">
            {oracles.map((o) => (
              <button key={o.id} type="button" className="btn-ghost text-xs" onClick={() => runOracle(o.id)}>
                {o.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-sm font-semibold text-muted mb-2">Shortcuts</h2>
          <div className="flex flex-wrap gap-1">
            {shortcuts.map((s) => (
              <button key={s.id} type="button" className="btn-ghost text-xs" onClick={() => runShortcut(s.id)}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-sm font-semibold text-muted mb-2">Lonelog</h2>
          <pre className="text-[10px] text-muted whitespace-pre-wrap font-mono max-h-40 overflow-y-auto">
            {lonelog.slice(-20).join("\n")}
          </pre>
        </div>
        {sources.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-muted mb-2">Sources</h2>
            <ul className="text-[10px] text-muted space-y-1">
              {sources.slice(0, 4).map((s, i) => (
                <li key={i}>{s.source_label} p.{s.page}</li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}
