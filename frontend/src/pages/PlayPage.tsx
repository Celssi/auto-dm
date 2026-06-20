import { useEffect, useReducer, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import PlayWizard from './play/PlayWizard';
import PlaySessionView from './play/PlaySessionView';
import { createInitialPlayState, playReducer } from './play/playState';
import { usePlayPageSession } from './play/usePlayPageSession';

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
    startNextAdventure,
  } = usePlayPageSession(state, dispatch, loadSeqRef, campaignIdRef);

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
      />
    );
  }

  return (
    <PlaySessionView
      state={state}
      bottomRef={bottomRef}
      onBegin={beginSession}
      onInputChange={(input) => dispatch({ type: 'set', patch: { input } })}
      onSend={() => sendMessage(state.input)}
      onConfirmSpellCast={() => state.spellConfirm && sendMessage('yes')}
      onCancelSpellCast={() => sendMessage('cancel spell')}
      onRunOracle={runOracle}
      onRunShortcut={runShortcut}
      onStartNextAdventure={startNextAdventure}
      onDiceModalUpdate={handleDiceModalUpdate}
      onDiceModalSubmit={handleDiceModalSubmit}
      onDiceModalClose={handleDiceModalClose}
    />
  );
}
