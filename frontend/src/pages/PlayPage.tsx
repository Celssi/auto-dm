import { useCallback, useEffect, useReducer, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, type ChatResult } from '../api/client';
import type { Character } from '../types';
import PlayWizard from './play/PlayWizard';
import PlaySessionView from './play/PlaySessionView';
import { createInitialPlayState, playReducer } from './play/playState';

export default function PlayPage() {
  const { sessionId: paramId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const campaignIdRef = useRef('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const [state, dispatch] = useReducer(
    playReducer,
    undefined,
    () => createInitialPlayState(paramId || '', searchParams.get('new') === '1' ? 'new' : 'continue'),
  );

  const loadMeta = useCallback(async () => {
    const [s, c, a, sh, or] = await Promise.all([
      api.listSessions(),
      api.listCharacters(),
      api.listAdventures(),
      api.getShortcuts(),
      api.getOracles(),
    ]);
    dispatch({
      type: 'set',
      patch: {
        sessions: s.sessions,
        characters: c.characters,
        adventures: a.adventures,
        shortcuts: sh.shortcuts,
        oracles: or.oracles,
        ...(s.sessions.length === 0 ? { wizardTab: 'new' as const } : {}),
        metaLoaded: true,
      },
    });
  }, []);

  const loadSession = useCallback(async (id: string) => {
    dispatch({ type: 'set', patch: { sessionLoaded: false } });
    const { session } = await api.getSession(id);
    const adventurePromise = session.adventure_id
      ? api.getAdventure(session.adventure_id).catch(() => null)
      : Promise.resolve(null);
    const [{ character: ch }, { summary }, log, adventureResult] = await Promise.all([
      api.getCharacter(session.character_id),
      api.getCharacterSummary(session.character_id),
      api.getLonelog(id),
      adventurePromise,
    ]);
    let journalEntities: typeof state.journalEntities = [];
    if (adventureResult?.adventure.campaign_id) {
      campaignIdRef.current = adventureResult.adventure.campaign_id;
      try {
        const { entities } = await api.getCampaignEntities(adventureResult.adventure.campaign_id);
        journalEntities = entities;
      } catch {
        journalEntities = [];
      }
    } else {
      campaignIdRef.current = '';
    }
    dispatch({
      type: 'set',
      patch: {
        messages: session.messages || [],
        includeFaerun: !!session.include_faerun,
        characterId: session.character_id,
        character: ch as Character,
        characterSummary: summary,
        lonelog: log.lines,
        journalEntities,
        sessionLoaded: true,
      },
    });
  }, []);

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

  const startSession = async () => {
    const res = await api.createSession({
      ...state.newSession,
      include_faerun: state.includeFaerun,
    });
    dispatch({ type: 'set', patch: { sessionId: res.id } });
    navigate(`/play/${res.id}`);
    await loadSession(res.id);
    await loadMeta();
  };

  const bootstrapAndPlay = async () => {
    const { newCampaign } = state;
    if (!newCampaign.character_id || !newCampaign.theme.trim()) return;
    dispatch({ type: 'set', patch: { bootstrapError: '', bootstrapping: true } });
    try {
      const result = await api.bootstrapCampaign({
        character_id: newCampaign.character_id,
        mode: newCampaign.mode,
        theme: newCampaign.theme.trim(),
        include_faerun: newCampaign.include_faerun,
        campaign_name: newCampaign.campaign_name.trim(),
      });
      dispatch({ type: 'set', patch: { sessionId: result.session_id } });
      navigate(`/play/${result.session_id}`);
      await loadSession(result.session_id);
      await loadMeta();
    } catch (e) {
      dispatch({
        type: 'set',
        patch: { bootstrapError: e instanceof Error ? e.message : 'Bootstrap failed' },
      });
    } finally {
      dispatch({ type: 'set', patch: { bootstrapping: false } });
    }
  };

  const sendMessage = async (msg: string) => {
    const { sessionId, loading } = state;
    if (!sessionId || !msg.trim() || loading) return;
    const text = msg.trim();
    dispatch({ type: 'set', patch: { input: '', spellConfirm: null, chatError: '' } });
    dispatch({ type: 'appendMessages', messages: [{ role: 'user', content: text }] });
    dispatch({ type: 'set', patch: { loading: true } });
    try {
      const result: ChatResult = await api.chat(sessionId, text);
      dispatch({
        type: 'appendMessages',
        messages: [{ role: 'assistant', content: result.response }],
      });
      dispatch({
        type: 'set',
        patch: {
          character: result.character as Character,
          sources: result.sources || [],
          spellConfirm: result.spell_confirmation ?? null,
        },
      });
      const log = await api.getLonelog(sessionId);
      dispatch({ type: 'set', patch: { lonelog: log.lines } });
      if (campaignIdRef.current) {
        api
          .getCampaignEntities(campaignIdRef.current)
          .then(({ entities }) => dispatch({ type: 'set', patch: { journalEntities: entities } }))
          .catch(() => {});
      }
    } catch (e) {
      dispatch({
        type: 'set',
        patch: { chatError: e instanceof Error ? e.message : 'Something went wrong talking to the DM.' },
      });
    } finally {
      dispatch({ type: 'set', patch: { loading: false } });
    }
  };

  const runOracle = async (id: string) => {
    if (!state.sessionId) return;
    dispatch({ type: 'set', patch: { loading: true } });
    try {
      const result = await api.runOracle(state.sessionId, id);
      dispatch({
        type: 'appendMessages',
        messages: [
          { role: 'user', content: `[oracle: ${id}]` },
          { role: 'assistant', content: String(result.summary) },
        ],
      });
      const log = await api.getLonelog(state.sessionId);
      dispatch({ type: 'set', patch: { lonelog: log.lines } });
    } finally {
      dispatch({ type: 'set', patch: { loading: false } });
    }
  };

  const runShortcut = async (id: string) => {
    if (!state.sessionId) return;
    dispatch({ type: 'set', patch: { loading: true } });
    try {
      const result = await api.runShortcut(state.sessionId, id);
      const text = String(result.user_message || result.summary || 'Shortcut executed.');
      dispatch({
        type: 'appendMessages',
        messages: [
          { role: 'user', content: `[${id}]` },
          { role: 'assistant', content: text },
        ],
      });
    } finally {
      dispatch({ type: 'set', patch: { loading: false } });
    }
  };

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
      onInputChange={(input) => dispatch({ type: 'set', patch: { input } })}
      onSend={() => sendMessage(state.input)}
      onConfirmSpellCast={() => state.spellConfirm && sendMessage('yes')}
      onCancelSpellCast={() => sendMessage('cancel spell')}
      onRunOracle={runOracle}
      onRunShortcut={runShortcut}
    />
  );
}
