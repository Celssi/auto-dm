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

  const reindex = async (includeFaerun: boolean) => {
    setIndexing(true);
    setIndexStatus('Indexing rulebooks. This window keeps the Cloud Run instance awake.');
    setMessage(null);
    try {
      const result: { ok?: boolean; chunk_count?: number } = {};
      let streamError = '';
      await api.reindex(includeFaerun, (event, data) => {
        if (event === 'progress' && data && typeof data === 'object' && 'message' in data) {
          setIndexStatus(String((data as { message: string }).message));
        } else if (event === 'done' && data && typeof data === 'object') {
          Object.assign(result, data);
        } else if (event === 'error' && data && typeof data === 'object' && 'detail' in data) {
          streamError = String((data as { detail: string }).detail);
        }
      });
      if (streamError) throw new Error(streamError);
      const ok = Boolean(result.ok);
      const msg = ok ? `Indexed ${result.chunk_count ?? 0} chunks` : 'Indexing failed';
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
      <PageHeader title="Settings" subtitle="Rules search, indexing, and system status." />

      {health && (
        <m.div variants={fadeUp} className="flex flex-wrap gap-2">
          <StatusBadge
            status={health.indexed ? 'ok' : 'warn'}
            label={health.indexed ? 'Rules index ready' : 'Not indexed'}
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
          <h2 className="display-title text-base">Rules search</h2>
        </div>
        {gameId === 'dnd5e' && (
          <Toggle
            checked={settings.include_faerun}
            onChange={(include_faerun) => setSettings({ ...settings, include_faerun })}
            label="Include Heroes of Faerûn & Adventures in Faerûn in rules search"
          />
        )}
        <Toggle
          checked={settings.use_rerank}
          onChange={(use_rerank) => setSettings({ ...settings, use_rerank })}
          label="Use cross-encoder reranking (Quality+)"
        />
        <button type="button" className="btn-primary" onClick={save}>
          Save settings
        </button>
      </m.div>

      <m.div variants={fadeUp} className="panel-glow p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Database size={18} className="text-accent" />
          <h2 className="display-title text-base">Index rulebooks</h2>
        </div>
        <p className="text-sm text-muted leading-relaxed">
          Uses the rulebooks in Cloud Storage. Keep this tab open during a long index so the connection stays alive and
          Cloud Run does not scale to zero.
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-ghost" disabled={indexing} onClick={() => reindex(false)}>
            {indexing ? 'Indexing…' : 'Index core (PHB, DMG, MM)'}
          </button>
          {gameId === 'dnd5e' && (
            <button type="button" className="btn-ghost" disabled={indexing} onClick={() => reindex(true)}>
              {indexing ? 'Indexing…' : 'Index core + Faerûn'}
            </button>
          )}
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
