import { useEffect, useReducer, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import PlayWizard from './play/PlayWizard';
import PlaySessionView from './play/PlaySessionView';
import { createInitialPlayState, playReducer } from './play/playState';
import { usePlayPageSession } from './play/usePlayPageSession';
import { useLoadedCharacterAdventure } from '../games/brambletrek/CampaignStartFields';
import { useGame } from '../context/GameContext';
import ErrorBoundary from '../components/ui/ErrorBoundary';

export default function PlayPage() {
  const { sessionId: paramId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const campaignIdRef = useRef('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const loadSeqRef = useRef(0);

  const [state, dispatch] = useReducer(playReducer, undefined, () =>
    createInitialPlayState(paramId || '', searchParams.get('new') === '1' ? 'new' : 'continue'),
  );

  const {
    loadMeta,
    loadSession,
    startSession,
    bootstrapAndPlay,
    beginSession,
    sendMessage,
    runOracle,
    runShortcut,
    handleDiceModalUpdate,
    handleDiceModalSubmit,
    handleDiceModalClose,
    handleSpellCastModalUpdate,
    handleSpellCastModalSubmit,
    handleSpellCastModalClose,
    startNextAdventure,
    handleJourneyApply,
    handleJourneyDrawItem,
    handleJourneyFinish,
    handleJourneyDiscard,
    handleJourneyStartCombat,
    handleDragonkeepAction,
    handleDragonkeepInit,
    handleBrambletrekCombatAction,
    handleCombatAction,
    rebuildSheet,
    toggleHeroicInspiration,
    renameSession,
    archiveSession,
    setStoryMode,
  } = usePlayPageSession(state, dispatch, loadSeqRef, campaignIdRef);

  const { gameId } = useGame();
  const campaignCharacter = state.characters.find((c) => c.id === state.newCampaign.character_id);
  const syncAdventure = !state.sessionId && (campaignCharacter?.game_id || gameId) === 'brambletrek';
  const loadedAdventure = useLoadedCharacterAdventure(state.newCampaign.character_id, syncAdventure);
  const [syncedAdventureCharacterId, setSyncedAdventureCharacterId] = useState('');
  if (!syncAdventure || !state.newCampaign.character_id) {
    if (syncedAdventureCharacterId) setSyncedAdventureCharacterId('');
  } else if (loadedAdventure !== undefined && syncedAdventureCharacterId !== state.newCampaign.character_id) {
    setSyncedAdventureCharacterId(state.newCampaign.character_id);
    dispatch({ type: 'patchNewCampaign', patch: { active_adventure: loadedAdventure } });
  }

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  useEffect(() => {
    if (paramId) {
      dispatch({ type: 'set', patch: { sessionId: paramId } });
      loadSession(paramId);
    }
  }, [paramId, loadSession]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.loading]);

  if (!state.sessionId) {
    return (
      <PlayWizard
        state={state}
        onWizardTabChange={(wizardTab) => dispatch({ type: 'set', patch: { wizardTab } })}
        onNavigateSession={(id) => navigate(`/play/${id}`)}
        onPatchNewSession={(patch) => dispatch({ type: 'patchNewSession', patch })}
        onPatchNewCampaign={(patch) => dispatch({ type: 'patchNewCampaign', patch })}
        onIncludeFaerunChange={(includeFaerun) => dispatch({ type: 'set', patch: { includeFaerun } })}
        onStartSession={startSession}
        onBootstrapAndPlay={bootstrapAndPlay}
        onRenameSession={renameSession}
        onArchiveSession={archiveSession}
      />
    );
  }

  return (
    <ErrorBoundary
      fallback={
        <div className="max-w-xl mx-auto p-6">
          <p className="text-sm text-danger rounded-lg border border-danger/30 bg-danger/10 px-4 py-3" role="alert">
            The play screen hit an error. Reload this page to restore the session. Your last queued message is kept and
            will send after reload.
          </p>
        </div>
      }
    >
      <PlaySessionView
        state={state}
        bottomRef={bottomRef}
        onBegin={beginSession}
        onInputChange={(input) => dispatch({ type: 'set', patch: { input } })}
        onSend={() => sendMessage(state.input)}
        onConfirmSpellCast={() =>
          state.spellConfirm && sendMessage(state.spellConfirm.free_use ? 'yes, Magic Initiate free' : 'yes')
        }
        onCancelSpellCast={() => sendMessage('cancel spell')}
        onRunOracle={runOracle}
        onRunShortcut={runShortcut}
        onStartNextAdventure={startNextAdventure}
        onDiceModalUpdate={handleDiceModalUpdate}
        onDiceModalSubmit={handleDiceModalSubmit}
        onDiceModalClose={handleDiceModalClose}
        onSpellCastModalUpdate={handleSpellCastModalUpdate}
        onSpellCastModalSubmit={handleSpellCastModalSubmit}
        onSpellCastModalClose={handleSpellCastModalClose}
        onJourneyApply={handleJourneyApply}
        onJourneyDrawItem={handleJourneyDrawItem}
        onJourneyFinish={handleJourneyFinish}
        onJourneyDiscard={handleJourneyDiscard}
        onJourneyStartCombat={handleJourneyStartCombat}
        onDragonkeepAction={handleDragonkeepAction}
        onDragonkeepInit={handleDragonkeepInit}
        onBrambletrekCombatAction={handleBrambletrekCombatAction}
        onCombatAction={handleCombatAction}
        onRebuildSheet={() => void rebuildSheet()}
        onToggleHeroicInspiration={(next) => void toggleHeroicInspiration(next)}
        onConfirmReaction={() => sendMessage('Yes, I use my reaction.')}
        onDeclineReaction={() => sendMessage('No, I do not use my reaction.')}
        onStoryModeChange={setStoryMode}
      />
    </ErrorBoundary>
  );
}
