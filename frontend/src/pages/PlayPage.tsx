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
  const loadSeqRef = useRef(0);

  const [state, dispatch] = useReducer(playReducer, undefined, () =>
    createInitialPlayState(paramId || '', searchParams.get('new') === '1' ? 'new' : 'continue'),
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
    const seq = ++loadSeqRef.current;
    dispatch({ type: 'set', patch: { sessionLoaded: false, loadError: '' } });
    try {
      const { session } = await api.getSession(id);
      if (seq !== loadSeqRef.current) return;

      const [{ character: ch }, { summary }, log] = await Promise.all([
        api.getCharacter(session.character_id),
        api.getCharacterSummary(session.character_id),
        api.getLonelog(id),
      ]);
      if (seq !== loadSeqRef.current) return;

      dispatch({
        type: 'set',
        patch: {
          messages: session.messages || [],
          includeFaerun: !!session.include_faerun,
          characterId: session.character_id,
          character: ch as Character,
          characterSummary: summary,
          lonelog: log.lines,
          adventureId: session.adventure_id || '',
          sessionLoaded: true,
        },
      });

      if (!session.adventure_id) {
        campaignIdRef.current = '';
        dispatch({
          type: 'set',
          patch: {
            campaignId: '',
            playerProgress: null,
            adventureComplete: false,
            nextAdventure: null,
            journalEntities: [],
          },
        });
        return;
      }

      const adventureResult = await api.getAdventure(session.adventure_id).catch(() => null);
      if (seq !== loadSeqRef.current) return;

      const adventure = adventureResult?.adventure;
      let journalEntities: typeof state.journalEntities = [];
      if (adventure?.campaign_id) {
        campaignIdRef.current = adventure.campaign_id;
        try {
          const { entities } = await api.getCampaignEntities(adventure.campaign_id);
          journalEntities = entities;
        } catch {
          journalEntities = [];
        }
      } else {
        campaignIdRef.current = '';
      }

      if (seq !== loadSeqRef.current) return;
      dispatch({
        type: 'set',
        patch: {
          journalEntities,
          campaignId: adventure?.campaign_id || '',
          playerProgress: adventure?.player_progress ?? null,
          adventureComplete: !!adventure?.player_progress?.adventure_complete,
          nextAdventure: null,
        },
      });
    } catch (e) {
      if (seq !== loadSeqRef.current) return;
      dispatch({
        type: 'set',
        patch: {
          sessionLoaded: true,
          loadError: e instanceof Error ? e.message : 'Failed to load session',
        },
      });
    }
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

  const beginSession = async () => {
    const { sessionId, loading, beginning } = state;
    if (!sessionId || loading || beginning) return;
    dispatch({ type: 'set', patch: { beginning: true, beginError: '' } });
    try {
      const result = await api.beginSession(sessionId);
      dispatch({
        type: 'set',
        patch: {
          messages: [result.message],
          beginning: false,
        },
      });
      const log = await api.getLonelog(sessionId);
      dispatch({ type: 'set', patch: { lonelog: log.lines } });
    } catch (e) {
      dispatch({
        type: 'set',
        patch: {
          beginError: e instanceof Error ? e.message : 'Failed to begin adventure',
          beginning: false,
        },
      });
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
          ...(result.player_progress ? { playerProgress: result.player_progress } : {}),
          adventureComplete: !!result.adventure_complete,
          nextAdventure: result.next_adventure ?? null,
          combatState: result.combat_state && result.combat_state.status === 'active' ? result.combat_state : null,
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

  const runShortcut = (id: string) => {
    sendMessage(`/${id}`);
  };

  const startNextAdventure = async () => {
    const nextId = state.nextAdventure?.id;
    if (!nextId || state.startingNext) return;
    dispatch({ type: 'set', patch: { startingNext: true } });
    try {
      const result = await api.startAdventureSession(nextId);
      navigate(`/play/${result.session_id}`);
      await loadSession(result.session_id);
      await loadMeta();
    } catch (e) {
      dispatch({
        type: 'set',
        patch: {
          chatError: e instanceof Error ? e.message : 'Failed to start next adventure.',
          startingNext: false,
        },
      });
      return;
    }
    dispatch({ type: 'set', patch: { startingNext: false, adventureComplete: false, nextAdventure: null } });
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
      onBegin={beginSession}
      onInputChange={(input) => dispatch({ type: 'set', patch: { input } })}
      onSend={() => sendMessage(state.input)}
      onConfirmSpellCast={() => state.spellConfirm && sendMessage('yes')}
      onCancelSpellCast={() => sendMessage('cancel spell')}
      onRunOracle={runOracle}
      onRunShortcut={runShortcut}
      onStartNextAdventure={startNextAdventure}
    />
  );
}
