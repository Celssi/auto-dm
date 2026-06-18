import { Link } from 'react-router-dom';
import { m, AnimatePresence } from '../../lib/framer';
import { Swords } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import TabBar from '../../components/ui/TabBar';
import EmptyState from '../../components/ui/EmptyState';
import ListLoading from '../../components/ui/ListLoading';
import AnimatedPage from '../../components/ui/AnimatedPage';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';
import ChoiceGroup from '../../components/ui/forms/ChoiceGroup';
import Toggle from '../../components/ui/forms/Toggle';
import SegmentedControl from '../../components/ui/forms/SegmentedControl';
import type { PlayMode, PlayState } from './playState';

interface Props {
  state: PlayState;
  onWizardTabChange: (tab: 'continue' | 'new') => void;
  onNavigateSession: (id: string) => void;
  onPatchNewSession: (patch: Partial<PlayState['newSession']>) => void;
  onPatchNewCampaign: (patch: Partial<PlayState['newCampaign']>) => void;
  onIncludeFaerunChange: (value: boolean) => void;
  onStartSession: () => void;
  onBootstrapAndPlay: () => void;
}

export default function PlayWizard({
  state,
  onWizardTabChange,
  onNavigateSession,
  onPatchNewSession,
  onPatchNewCampaign,
  onIncludeFaerunChange,
  onStartSession,
  onBootstrapAndPlay,
}: Props) {
  const {
    metaLoaded,
    sessions,
    characters,
    adventures,
    wizardTab,
    newSession,
    newCampaign,
    includeFaerun,
    bootstrapError,
    bootstrapping,
  } = state;

  return (
    <AnimatedPage className="max-w-xl mx-auto space-y-6">
      <PageHeader title="Play" subtitle="Continue an existing session or generate a new campaign." />

      <TabBar
        tabs={[
          { id: 'continue', label: 'Continue' },
          { id: 'new', label: 'New campaign' },
        ]}
        active={wizardTab}
        onChange={(id) => onWizardTabChange(id as 'continue' | 'new')}
      />

      <AnimatePresence mode="wait">
        {wizardTab === 'continue' && (
          <m.div
            key="continue"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="panel-glow p-5 space-y-4"
          >
            {!metaLoaded ? (
              <ListLoading />
            ) : sessions.length > 0 ? (
              <div className="space-y-1">
                <p className="label-text mb-2">Recent sessions</p>
                {sessions.slice(0, 8).map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className="block w-full text-left py-2.5 px-3 text-sm rounded-lg hover:bg-accent/10 hover:text-accent border border-transparent hover:border-accent/20 transition-colors"
                    onClick={() => onNavigateSession(s.id)}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<Swords size={28} />}
                title="No sessions yet"
                description="Start a new campaign below to begin your adventure."
              />
            )}

            <details className="text-sm group">
              <summary className="cursor-pointer text-muted hover:text-accent transition-colors label-text">
                Advanced: link existing adventure
              </summary>
              <div className="mt-4 space-y-4 pl-3 border-l-2 border-accent/20">
                <Field label="Character">
                  <ChoiceGroup
                    value={newSession.character_id}
                    onChange={(character_id) => onPatchNewSession({ character_id })}
                    options={characters.map((c) => ({ value: c.id, label: c.name }))}
                    allowEmpty
                    emptyLabel="Select character"
                    columns={2}
                  />
                </Field>
                <Field label="Adventure">
                  <ChoiceGroup
                    value={newSession.adventure_id}
                    onChange={(adventure_id) => onPatchNewSession({ adventure_id })}
                    options={adventures.map((a) => ({ value: a.id, label: a.name }))}
                    allowEmpty
                    emptyLabel="Select adventure"
                    columns={2}
                  />
                </Field>
                <Field label="Session name (optional)">
                  <TextInput
                    placeholder="Session name"
                    value={newSession.name}
                    onChange={(e) => onPatchNewSession({ name: e.target.value })}
                  />
                </Field>
                <Toggle
                  checked={includeFaerun}
                  onChange={onIncludeFaerunChange}
                  label="Include Faerûn supplements in rules search"
                />
                <button
                  type="button"
                  className="btn-primary w-full"
                  disabled={!newSession.character_id || !newSession.adventure_id}
                  onClick={onStartSession}
                >
                  Begin play
                </button>
              </div>
            </details>
          </m.div>
        )}

        {wizardTab === 'new' && (
          <m.div
            key="new"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="panel-glow p-5 space-y-4"
          >
            <p className="text-sm text-muted leading-relaxed">
              Generate a campaign, adventure, journal entries, and opening scene, then jump straight into play.
            </p>

            <Field label="Character">
              <ChoiceGroup
                value={newCampaign.character_id}
                onChange={(character_id) => onPatchNewCampaign({ character_id })}
                options={characters.map((c) => ({ value: c.id, label: c.name }))}
                allowEmpty
                emptyLabel="Select character"
                columns={2}
              />
            </Field>
            {metaLoaded && characters.length === 0 && (
              <p className="text-xs text-muted">
                <Link to="/characters" className="text-accent hover:underline">
                  Create a character
                </Link>{' '}
                first.
              </p>
            )}

            <Field label="Campaign type">
              <SegmentedControl
                value={newCampaign.mode}
                onChange={(mode) => onPatchNewCampaign({ mode: mode as PlayMode })}
                options={[
                  { value: 'freeform', label: 'Freeform' },
                  { value: 'module', label: 'Module (RAG)' },
                ]}
              />
            </Field>

            <Field label="Theme / hook">
              <TextArea
                placeholder="e.g. A haunted mine near Waterdeep"
                value={newCampaign.theme}
                onChange={(e) => onPatchNewCampaign({ theme: e.target.value })}
                className="min-h-[80px]"
              />
            </Field>

            <Field label="Campaign name (optional)">
              <TextInput
                placeholder="Campaign name"
                value={newCampaign.campaign_name}
                onChange={(e) => onPatchNewCampaign({ campaign_name: e.target.value })}
              />
            </Field>

            <Toggle
              checked={newCampaign.include_faerun}
              onChange={(include_faerun) => onPatchNewCampaign({ include_faerun })}
              label="Use Faerûn supplements (Heroes & Adventures)"
            />

            {bootstrapError && (
              <p className="text-sm text-danger rounded-lg border border-danger/30 bg-danger/10 px-3 py-2">
                {bootstrapError}
              </p>
            )}

            <button
              type="button"
              className="btn-primary w-full py-2.5"
              disabled={!newCampaign.character_id || !newCampaign.theme.trim() || bootstrapping}
              onClick={onBootstrapAndPlay}
            >
              {bootstrapping ? 'Generating campaign… (30-60 s)' : 'Generate & play'}
            </button>
          </m.div>
        )}
      </AnimatePresence>
    </AnimatedPage>
  );
}
