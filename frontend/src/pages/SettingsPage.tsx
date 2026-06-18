import { useEffect, useState } from 'react';
import { m } from '../lib/framer';
import { Database, Settings2, Sparkles } from 'lucide-react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import Toggle from '../components/ui/forms/Toggle';
import AnimatedPage from '../components/ui/AnimatedPage';
import { fadeUp } from '../components/ui/motion';

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
    setMessage('Settings saved.');
  };

  const reindex = async (includeFaerun: boolean) => {
    setIndexing(true);
    setMessage(null);
    try {
      const r = await api.reindex(includeFaerun);
      setMessage(r.ok ? `Indexed ${r.chunk_count} chunks.` : 'Indexing failed.');
      const h = await api.health();
      setHealth(h);
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
            label={health.claude_configured ? 'Claude API configured' : 'Missing API key'}
          />
        </m.div>
      )}

      <m.div variants={fadeUp} className="panel-glow p-5 space-y-5">
        <div className="flex items-center gap-2">
          <Settings2 size={18} className="text-accent" />
          <h2 className="font-display font-semibold text-gray-100">Rules search</h2>
        </div>
        <Toggle
          checked={settings.include_faerun}
          onChange={(include_faerun) => setSettings({ ...settings, include_faerun })}
          label="Include Heroes of Faerûn & Adventures in Faerûn in rules search"
        />
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
          <h2 className="font-display font-semibold text-gray-100">Index rulebooks</h2>
        </div>
        <p className="text-sm text-muted leading-relaxed">
          Requires Ollama with nomic-embed-text. First run may take hours with OCR.
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-ghost" disabled={indexing} onClick={() => reindex(false)}>
            {indexing ? 'Indexing…' : 'Index core (PHB, DMG, MM)'}
          </button>
          <button type="button" className="btn-ghost" disabled={indexing} onClick={() => reindex(true)}>
            {indexing ? 'Indexing…' : 'Index core + Faerûn'}
          </button>
        </div>
      </m.div>

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
