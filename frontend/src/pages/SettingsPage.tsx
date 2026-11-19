import { useEffect, useState } from 'react';
import { m } from '../lib/framer';
import { Database, Download, Settings2, Sparkles } from 'lucide-react';
import { usePWA } from '../hooks/usePWA';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import Toggle from '../components/ui/forms/Toggle';
import AnimatedPage from '../components/ui/AnimatedPage';
import { fadeUp } from '../components/ui/motion';
import { useToast } from '../components/ui/toast';
import LongJobOverlay from '../components/LongJobOverlay';
import { useGame } from '../context/GameContext';

export default function SettingsPage() {
  const { gameId } = useGame();
  const toast = useToast();
  const { isInstallable, isInstalled, installPWA } = usePWA();
  const [settings, setSettings] = useState({ include_faerun: false, use_rerank: true });
  const [health, setHealth] = useState<{
    indexed: boolean;
    indexed_by_game?: Record<string, boolean>;
    chunk_counts?: Record<string, number>;
    claude_configured: boolean;
    claude_model?: string;
  } | null>(null);
  const [indexing, setIndexing] = useState(false);
  const [indexStatus, setIndexStatus] = useState('Indexing rulebooks.');
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getSettings().then((r) => setSettings(r.settings));
    api.health().then(setHealth);
  }, []);

  const save = async () => {
    try {
      const r = await api.updateSettings(settings);
      setSettings(r.settings);
      setMessage(null);
      toast.success('Settings saved');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to save settings';
      toast.error(msg);
      setMessage(msg);
    }
  };

  const reindex = async (
    includeFaerun: boolean,
    confirmDropFaerun = false,
    targetGameId = 'dnd5e',
  ) => {
    setIndexing(true);
    setIndexStatus('Indexing rulebooks. This window keeps the Cloud Run instance awake.');
    setMessage(null);
    try {
      const result: {
        ok?: boolean;
        chunk_count?: number;
        chunk_counts?: Record<string, number>;
      } = {};
      let streamError = '';
      await api.reindex(
        includeFaerun,
        (event, data) => {
          if (event === 'progress' && data && typeof data === 'object' && 'message' in data) {
            setIndexStatus(String((data as { message: string }).message));
          } else if (event === 'done' && data && typeof data === 'object') {
            Object.assign(result, data);
          } else if (event === 'error' && data && typeof data === 'object' && 'detail' in data) {
            streamError = String((data as { detail: string }).detail);
          }
        },
        confirmDropFaerun,
        targetGameId,
      );
      if (streamError) throw new Error(streamError);
      const ok = Boolean(result.ok);
      const counts = result.chunk_counts;
      const countText = counts
        ? Object.entries(counts)
            .map(([id, n]) => `${id}: ${n}`)
            .join(', ')
        : String(result.chunk_count ?? 0);
      const msg = ok ? `Indexed ${countText} chunks` : 'Indexing failed';
      if (ok) toast.success(msg);
      else toast.error(msg);
      setMessage(ok ? `${msg}.` : msg);
      const h = await api.health();
      setHealth(h);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Indexing failed';
      toast.error(msg);
      setMessage(msg);
    } finally {
      setIndexing(false);
    }
  };

  return (
    <AnimatedPage className="max-w-2xl space-y-8">
      <PageHeader title="Settings" subtitle="Player preferences, then admin tools for this app." />

      {health && (
        <m.div variants={fadeUp} className="flex flex-wrap gap-2">
          <StatusBadge
            status={health.indexed_by_game?.dnd5e || health.indexed ? 'ok' : 'warn'}
            label={
              health.indexed_by_game?.dnd5e || health.indexed
                ? `D&D 5e index ready${health.chunk_counts?.dnd5e != null ? ` (${health.chunk_counts.dnd5e})` : ''}`
                : 'D&D 5e not indexed'
            }
          />
          <StatusBadge
            status={health.indexed_by_game?.brambletrek ? 'ok' : 'warn'}
            label={
              health.indexed_by_game?.brambletrek
                ? `Brambletrek index ready${health.chunk_counts?.brambletrek != null ? ` (${health.chunk_counts.brambletrek})` : ''}`
                : 'Brambletrek not indexed'
            }
          />
          <StatusBadge
            status={health.claude_configured ? 'ok' : 'error'}
            label={
              health.claude_configured
                ? `Claude API configured (${health.claude_model || 'unknown'})`
                : 'Missing API key'
            }
          />
        </m.div>
      )}

      {isInstallable && !isInstalled && (
        <m.div variants={fadeUp}>
          <button type="button" className="btn-ghost inline-flex items-center gap-2" onClick={() => void installPWA()}>
            <Download size={16} />
            Install app
          </button>
        </m.div>
      )}

      <m.div variants={fadeUp} className="panel-glow p-5 space-y-5">
        <div className="flex items-center gap-2">
          <Settings2 size={18} className="text-accent" />
          <h2 className="display-title text-base">Player</h2>
        </div>
        <p className="text-sm text-muted leading-relaxed">
          These options are defaults. You can still turn Faerun books on or off when you start a
          session.
        </p>
        {gameId === 'dnd5e' && (
          <Toggle
            checked={settings.include_faerun}
            onChange={(include_faerun) => setSettings({ ...settings, include_faerun })}
            label="Include Heroes of Faerûn and Adventures in Faerûn in rules search"
            description="Default for new D&D sessions. Forgotten Realms names and adventures stay out of search unless this is on."
          />
        )}
        <button type="button" className="btn-primary" onClick={save}>
          Save settings
        </button>
      </m.div>

      <m.div variants={fadeUp} className="panel-glow p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Database size={18} className="text-accent" />
          <h2 className="display-title text-base">Admin</h2>
        </div>
        <p className="text-sm text-muted leading-relaxed">
          Indexing and search quality tools. Keep this tab open during a long index so the connection stays alive.
        </p>
        <Toggle
          checked={settings.use_rerank}
          onChange={(use_rerank) => setSettings({ ...settings, use_rerank })}
          label="Use cross-encoder reranking (Quality+)"
          description="Slower rules search, better ranking. Leave on unless a search is hanging."
        />
        <button type="button" className="btn-ghost" onClick={save}>
          Save admin settings
        </button>
        <p className="text-sm text-muted leading-relaxed">
          Index core only removes Heroes of Faerun and Adventures in Faerun from the D&D index. Prefer
          Index core + Faerun, or Index all books, unless you intend to drop those books. Brambletrek
          lives in a separate index, so D&D indexing does not replace it.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-primary"
            disabled={indexing}
            onClick={() => void reindex(true, false, 'all')}
          >
            {indexing ? 'Indexing…' : 'Index all books (D&D + Faerun + Brambletrek)'}
          </button>
          <button
            type="button"
            className="btn-ghost"
            disabled={indexing}
            onClick={() => void reindex(true, false, 'dnd5e')}
          >
            {indexing ? 'Indexing…' : 'Index core + Faerun'}
          </button>
          <button
            type="button"
            className="btn-ghost"
            disabled={indexing}
            onClick={() => void reindex(false, false, 'brambletrek')}
          >
            {indexing ? 'Indexing…' : 'Index Brambletrek'}
          </button>
          <button
            type="button"
            className="btn-ghost"
            disabled={indexing}
            onClick={() => {
              const ok = window.confirm(
                'Index core only deletes Faerun books from the rules index. Continue only if you want that.',
              );
              if (ok) void reindex(false, true, 'dnd5e');
            }}
          >
            {indexing ? 'Indexing…' : 'Index core (PHB, DMG, MM)'}
          </button>
        </div>
      </m.div>

      <LongJobOverlay active={indexing} title="Indexing rulebooks" message={indexStatus} />

      {message && (
        <m.p
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-sm text-accent flex items-center gap-2"
        >
          <Sparkles size={14} /> {message}
        </m.p>
      )}
    </AnimatedPage>
  );
}
