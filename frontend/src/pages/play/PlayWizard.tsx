import { Link } from 'react-router-dom';
import { m, AnimatePresence } from '../../lib/framer';
import PageHeader from '../../components/ui/PageHeader';
import TabBar from '../../components/ui/TabBar';
import AnimatedPage from '../../components/ui/AnimatedPage';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';
import ChoiceGroup from '../../components/ui/forms/ChoiceGroup';
import Toggle from '../../components/ui/forms/Toggle';
import SegmentedControl from '../../components/ui/forms/SegmentedControl';
import type { PlayMode, PlayState } from './playState';
import { getGamePlayConfig } from '../../games/play/registry';
import BrambletrekCampaignStartFields from '../../games/brambletrek/CampaignStartFields';
import { useGame } from '../../context/GameContext';
import { filterByGame, sessionMatchesGame } from '../../lib/gameScope';
import type { GameId } from '../../games/registry';
import LongJobOverlay from '../../components/LongJobOverlay';
import SessionManageList from '../../components/play/SessionManageList';

interface Props {
  state: PlayState;
  onWizardTabChange: (tab: 'continue' | 'new') => void;
  onNavigateSession: (id: string) => void;
  onPatchNewSession: (patch: Partial<PlayState['newSession']>) => void;
  onPatchNewCampaign: (patch: Partial<PlayState['newCampaign']>) => void;
  onIncludeFaerunChange: (value: boolean) => void;
  onStartSession: () => void;
  onBootstrapAndPlay: () => void;
  onRenameSession: (id: string, name: string) => Promise<void>;
  onArchiveSession: (id: string, archived: boolean) => Promise<void>;
}

function playWizardContext(state: PlayState, gameId: GameId) {
  const characters = filterByGame(state.characters, gameId);
  const gameAdventures = filterByGame(state.adventures, gameId);
  const sessions = state.sessions.filter((session) => sessionMatchesGame(session, state.characters, gameId));
  return { characters, gameAdventures, sessions, campaignPlay: getGamePlayConfig(gameId) };
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
  onRenameSession,
  onArchiveSession,
}: Props) {
  const { gameId } = useGame();
  const { metaLoaded, wizardTab, newSession, newCampaign, includeFaerun, bootstrapError, bootstrapping } = state;

  const { characters, gameAdventures, sessions, campaignPlay } = playWizardContext(state, gameId);

  return (
    <AnimatedPage className="max-w-xl mx-auto space-y-6">
      <LongJobOverlay
        active={bootstrapping}
        title="Generating campaign"
        message="Keep this tab open. Heartbeats keep Cloud Run from scaling to zero."
      />
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
          <PlayContinueTab
            metaLoaded={metaLoaded}
            sessions={sessions}
            characters={characters}
            gameAdventures={gameAdventures}
            newSession={newSession}
            includeFaerun={includeFaerun}
            showFaerun={campaignPlay.showFaerunToggle}
            onNavigateSession={onNavigateSession}
            onRenameSession={onRenameSession}
            onArchiveSession={onArchiveSession}
            onPatchNewSession={onPatchNewSession}
            onIncludeFaerunChange={onIncludeFaerunChange}
            onStartSession={onStartSession}
          />
        )}
        {wizardTab === 'new' && (
          <PlayNewCampaignTab
            metaLoaded={metaLoaded}
            characters={characters}
            newCampaign={newCampaign}
            campaignPlay={campaignPlay}
            bootstrapError={bootstrapError}
            bootstrapping={bootstrapping}
            onPatchNewCampaign={onPatchNewCampaign}
            onBootstrapAndPlay={onBootstrapAndPlay}
          />
        )}
      </AnimatePresence>
    </AnimatedPage>
  );
}

function PlayContinueTab({
  metaLoaded,
  sessions,
  characters,
  gameAdventures,
  newSession,
  includeFaerun,
  showFaerun,
  onNavigateSession,
  onRenameSession,
  onArchiveSession,
  onPatchNewSession,
  onIncludeFaerunChange,
  onStartSession,
}: {
  metaLoaded: boolean;
  sessions: PlayState['sessions'];
  characters: PlayState['characters'];
  gameAdventures: PlayState['adventures'];
  newSession: PlayState['newSession'];
  includeFaerun: boolean;
  showFaerun: boolean;
  onNavigateSession: (id: string) => void;
  onRenameSession: (id: string, name: string) => Promise<void>;
  onArchiveSession: (id: string, archived: boolean) => Promise<void>;
  onPatchNewSession: (patch: Partial<PlayState['newSession']>) => void;
  onIncludeFaerunChange: (value: boolean) => void;
  onStartSession: () => void;
}) {
  return (
    <m.div
      key="continue"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="panel-glow p-5 space-y-4"
    >
      <SessionManageList
        metaLoaded={metaLoaded}
        sessions={sessions}
        onNavigateSession={onNavigateSession}
        onRenameSession={onRenameSession}
        onArchiveSession={onArchiveSession}
      />
      <details className="text-sm group">
        <summary className="cursor-pointer text-muted hover:text-accent transition-colors label-text">
          Advanced: link existing adventure
        </summary>
        <div className="mt-4 space-y-4 pl-3 border-l-2 border-accent/20">
          <Field label="Character">
            <ChoiceGroup
              value={newSession.character_id}
              onChange={(character_id) => onPatchNewSession({ character_id, adventure_id: '' })}
              options={characters.map((c) => ({
                value: c.id,
                label: c.name,
              }))}
              allowEmpty
              emptyLabel="Select character"
              columns={2}
            />
          </Field>
          <Field label="Adventure">
            <ChoiceGroup
              value={newSession.adventure_id}
              onChange={(adventure_id) => onPatchNewSession({ adventure_id })}
              options={gameAdventures.map((a) => ({ value: a.id, label: a.name }))}
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
          {showFaerun && (
            <Toggle
              checked={includeFaerun}
              onChange={onIncludeFaerunChange}
              label="Include Faerûn supplements in rules search"
            />
          )}
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
  );
}

function PlayNewCampaignTab({
  metaLoaded,
  characters,
  newCampaign,
  campaignPlay,
  bootstrapError,
  bootstrapping,
  onPatchNewCampaign,
  onBootstrapAndPlay,
}: {
  metaLoaded: boolean;
  characters: PlayState['characters'];
  newCampaign: PlayState['newCampaign'];
  campaignPlay: ReturnType<typeof getGamePlayConfig>;
  bootstrapError: string;
  bootstrapping: boolean;
  onPatchNewCampaign: (patch: Partial<PlayState['newCampaign']>) => void;
  onBootstrapAndPlay: () => void;
}) {
  if (!campaignPlay.usesAiCampaignGeneration) {
    return (
      <m.div
        key="new"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        className="panel-glow p-5 space-y-4"
      >
        <BrambletrekCampaignStartFields
          characters={characters}
          characterId={newCampaign.character_id}
          onCharacterIdChange={(character_id) => onPatchNewCampaign({ character_id })}
          activeAdventure={newCampaign.active_adventure}
          onActiveAdventureChange={(active_adventure) => onPatchNewCampaign({ active_adventure })}
          campaignName={newCampaign.campaign_name}
          onCampaignNameChange={(campaign_name) => onPatchNewCampaign({ campaign_name })}
          flavorNotes={newCampaign.theme}
          onFlavorNotesChange={(theme) => onPatchNewCampaign({ theme })}
          onSubmit={onBootstrapAndPlay}
          submitting={bootstrapping}
          showActions={false}
        />
        {bootstrapError && (
          <p className="text-sm text-danger rounded-lg border border-danger/30 bg-danger/10 px-3 py-2">
            {bootstrapError}
          </p>
        )}
        <button
          type="button"
          className="btn-primary w-full py-2.5"
          disabled={!newCampaign.character_id || bootstrapping}
          onClick={onBootstrapAndPlay}
        >
          {bootstrapping ? 'Starting adventure…' : 'Start adventure'}
        </button>
      </m.div>
    );
  }
  return (
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
          options={characters.map((c) => ({
            value: c.id,
            label: c.name,
          }))}
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
      {campaignPlay.showFaerunToggle && (
        <Toggle
          checked={newCampaign.include_faerun}
          onChange={(include_faerun) => onPatchNewCampaign({ include_faerun })}
          label="Use Faerûn supplements (Heroes & Adventures)"
        />
      )}
      {bootstrapError && (
        <p className="text-sm text-danger rounded-lg border border-danger/30 bg-danger/10 px-3 py-2">
          {bootstrapError}
        </p>
      )}
      <button
        type="button"
        className="btn-primary w-full py-2.5"
        disabled={
          !newCampaign.character_id ||
          (campaignPlay.campaignThemeRequired && !newCampaign.theme.trim()) ||
          bootstrapping
        }
        onClick={onBootstrapAndPlay}
      >
        {bootstrapping ? 'Generating campaign… (30-60 s)' : 'Generate & play'}
      </button>
    </m.div>
  );
}
