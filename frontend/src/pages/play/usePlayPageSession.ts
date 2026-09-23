import { useCallback, type Dispatch, type MutableRefObject } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type ChatResult } from '../../api/client';
import type { Character } from '../../types';
import { type DiceModalState, type PlayAction, type PlayState } from './playState';
import { getPlaySessionExtensions } from '../../games/brambletrek/playSession';
import { DEFAULT_GAME_ID } from '../../games/registry';
import { getGamePlayConfig } from '../../games/play/registry';
import { bootstrapBrambletrekSession } from '../../games/brambletrek/bootstrapCampaign';

import { initiativeMod } from '../../games/dnd5e/character-sheet/sheetUtils';

const DICE_SHORTCUTS = new Set(['ability_check', 'saving_throw', 'attack_roll', 'initiative', 'death_save']);

const SHORTCUT_LABELS: Record<string, string> = {
  ability_check: 'Ability Check',
  saving_throw: 'Saving Throw',
  attack_roll: 'Attack Roll',
  initiative: 'Initiative',
  death_save: 'Death Save',
};

export function usePlayPageSession(
  state: PlayState,
  dispatch: Dispatch<PlayAction>,
  loadSeqRef: MutableRefObject<number>,
  campaignIdRef: MutableRefObject<string>,
) {
  const navigate = useNavigate();

  const refreshSessionLogs = useCallback(
    async (sessionId: string) => {
      const [log, audit] = await Promise.all([api.getLonelog(sessionId), api.getAudit(sessionId)]);
      dispatch({ type: 'set', patch: { lonelog: log.lines, auditEvents: audit.events } });
    },
    [dispatch],
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
  }, [dispatch]);

  const refreshJourney = useCallback(
    async (sessionId: string, gameId: string) => {
      await getPlaySessionExtensions(gameId).refreshJourney(sessionId, dispatch);
    },
    [dispatch],
  );

  const loadSession = useCallback(
    async (id: string) => {
      if (!id) return;
      const seq = ++loadSeqRef.current;
      dispatch({ type: 'set', patch: { sessionLoaded: false, loadError: '' } });
      try {
        const { session } = await api.getSession(id);
        if (seq !== loadSeqRef.current || !session.character_id) return;

        const fetchCore = () =>
          Promise.all([
            api.getCharacter(session.character_id),
            api.getCharacterSummary(session.character_id),
            api.getLonelog(id),
            api.getAudit(id),
          ] as const);

        if (!session.adventure_id) {
          if (seq !== loadSeqRef.current) return;
          const [{ character: ch }, { summary }, log, audit] = await fetchCore();
          const gameId = String((ch as Character).game_id || 'dnd5e');
          const { shortcuts: sessionShortcuts } = await api.getShortcuts(gameId, session.character_id);
          campaignIdRef.current = '';
          dispatch({
            type: 'set',
            patch: {
              messages: session.messages || [],
              includeFaerun: !!session.include_faerun,
              characterId: session.character_id,
              character: ch as Character,
              characterSummary: summary,
              lonelog: log.lines,
              auditEvents: audit.events,
              adventureId: '',
              sessionLoaded: true,
              journalEntities: [],
              campaignId: '',
              playerProgress: null,
              adventureComplete: false,
              nextAdventure: null,
              shortcuts: sessionShortcuts,
            },
          });
          if (gameId) await refreshJourney(id, gameId);
          return;
        }

        if (seq !== loadSeqRef.current) return;
        const [[{ character: ch }, { summary }, log, audit], adventureResult] = await Promise.all([
          fetchCore(),
          api.getAdventure(session.adventure_id).catch(() => null),
        ]);
        if (seq !== loadSeqRef.current || !ch) return;

        const adventure = adventureResult?.adventure;
        let journalEntities: PlayState['journalEntities'] = [];
        let campaignId = '';
        let playerProgress = null;
        let adventureComplete = false;

        if (adventure?.campaign_id) {
          campaignIdRef.current = adventure.campaign_id;
          campaignId = adventure.campaign_id;
          try {
            const { entities } = await api.getCampaignEntities(adventure.campaign_id);
            journalEntities = entities;
          } catch {
            journalEntities = [];
          }
        } else {
          campaignIdRef.current = '';
        }
        playerProgress = adventure?.player_progress ?? null;
        adventureComplete = !!adventure?.player_progress?.adventure_complete;

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
            auditEvents: audit.events,
            adventureId: session.adventure_id,
            sessionLoaded: true,
            journalEntities,
            campaignId,
            playerProgress,
            adventureComplete,
            nextAdventure: null,
            shortcuts: (await api.getShortcuts(String((ch as Character).game_id || 'dnd5e'), session.character_id))
              .shortcuts,
          },
        });
        const loadedGameId = String((ch as Character).game_id || 'dnd5e');
        if (loadedGameId) await refreshJourney(id, loadedGameId);
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
    },
    [dispatch, loadSeqRef, campaignIdRef, refreshJourney],
  );

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
    const { newCampaign, characters } = state;
    if (!newCampaign.character_id) return;
    const selected = characters.find((c) => c.id === newCampaign.character_id);
    const playConfig = getGamePlayConfig(selected?.game_id || DEFAULT_GAME_ID);
    if (playConfig.campaignThemeRequired && !newCampaign.theme.trim()) return;
    dispatch({ type: 'set', patch: { bootstrapError: '', bootstrapping: true } });
    try {
      const result = playConfig.usesAiCampaignGeneration
        ? await api.bootstrapCampaign({
            character_id: newCampaign.character_id,
            mode: newCampaign.mode,
            theme: newCampaign.theme.trim(),
            include_faerun: newCampaign.include_faerun,
            campaign_name: newCampaign.campaign_name.trim(),
          })
        : await bootstrapBrambletrekSession({
            characterId: newCampaign.character_id,
            activeAdventure: newCampaign.active_adventure,
            campaignName: newCampaign.campaign_name,
            flavorNotes: newCampaign.theme,
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
      await refreshSessionLogs(sessionId);
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
      await refreshSessionLogs(sessionId);
      const chatGameId = String((result.character as Character)?.game_id || state.character?.game_id || 'dnd5e');
      await getPlaySessionExtensions(chatGameId).afterChat(sessionId, dispatch);
      if (campaignIdRef.current) {
        api
          .getCampaignEntities(campaignIdRef.current)
          .then(({ entities }) => dispatch({ type: 'set', patch: { journalEntities: entities } }))
          .catch((err: unknown) => console.warn('Failed to refresh journal entities', err));
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
      await refreshSessionLogs(state.sessionId);
    } finally {
      dispatch({ type: 'set', patch: { loading: false } });
    }
  };

  const runShortcut = async (id: string) => {
    if (!state.sessionId) return;
    const gameId = state.character?.game_id ?? 'dnd5e';
    const ext = getPlaySessionExtensions(gameId);
    if (await ext.runShortcut(state.sessionId, id, dispatch, refreshSessionLogs)) {
      return;
    }
    if (!DICE_SHORTCUTS.has(id) || !state.character) {
      sendMessage(`/${id}`);
      return;
    }
    const char = state.character;
    const showAbility = ['ability_check', 'saving_throw', 'attack_roll'].includes(id);
    const defaultAbility = id === 'initiative' ? 'dex' : 'str';
    const isProfSave = id === 'saving_throw' && (char.save_proficiencies ?? []).includes(defaultAbility);
    const defaultProf = isProfSave;
    const scores = char.ability_scores ?? {};
    const score = scores[defaultAbility] ?? 10;
    let mod =
      id === 'initiative'
        ? initiativeMod(char)
        : Math.floor((score - 10) / 2) + (defaultProf ? 2 + Math.floor((Math.max(1, char.level) - 1) / 4) : 0);

    const modal: DiceModalState = {
      shortcutId: id,
      label: SHORTCUT_LABELS[id] ?? id,
      ability: defaultAbility,
      advantage: 'normal',
      proficient: defaultProf,
      modifier: mod,
      diceCount: 1,
      hasModifier: id !== 'death_save',
      showAbilityPicker: showAbility,
      showProficiency: ['ability_check', 'saving_throw'].includes(id),
      mode: 'auto',
      manualValues: [null],
      autoResult: null,
      rolling: false,
      submitting: false,
    };
    dispatch({ type: 'set', patch: { diceModal: modal } });
  };

  const handleDiceModalUpdate = (patch: Partial<DiceModalState>) => {
    if (!state.diceModal) return;
    dispatch({ type: 'set', patch: { diceModal: { ...state.diceModal, ...patch } } });
  };

  const handleDiceModalSubmit = async (preRolled?: number[]) => {
    const modal = state.diceModal;
    if (!modal || !state.sessionId) return;

    const isAutoRoll = !preRolled;

    dispatch({
      type: 'set',
      patch: { diceModal: { ...modal, submitting: true, rolling: isAutoRoll } },
    });

    try {
      const params: Record<string, unknown> = {
        ability: modal.ability,
        advantage: modal.advantage,
        proficient: modal.proficient,
      };
      const result = await api.rollShortcut(state.sessionId, modal.shortcutId, params, preRolled);

      const rolls = result.shortcut?.dice?.rolls;

      if (isAutoRoll && rolls) {
        dispatch({
          type: 'set',
          patch: { diceModal: { ...modal, autoResult: rolls, rolling: true, submitting: true } },
        });
        await new Promise((r) => setTimeout(r, 1200));
        dispatch({
          type: 'set',
          patch: { diceModal: { ...modal, autoResult: rolls, rolling: false, submitting: true } },
        });
        await new Promise((r) => setTimeout(r, 800));
      }

      const userMsg = result.shortcut?.user_message ?? `/${modal.shortcutId}`;
      dispatch({
        type: 'appendMessages',
        messages: [
          { role: 'user', content: userMsg },
          { role: 'assistant', content: result.response },
        ],
      });
      dispatch({
        type: 'set',
        patch: {
          diceModal: null,
          character: result.character as Character,
          sources: result.sources || [],
          spellConfirm: result.spell_confirmation ?? null,
          ...(result.player_progress ? { playerProgress: result.player_progress } : {}),
          adventureComplete: !!result.adventure_complete,
          nextAdventure: result.next_adventure ?? null,
          combatState: result.combat_state && result.combat_state.status === 'active' ? result.combat_state : null,
        },
      });
      await refreshSessionLogs(state.sessionId);
      if (campaignIdRef.current) {
        api
          .getCampaignEntities(campaignIdRef.current)
          .then(({ entities }) => dispatch({ type: 'set', patch: { journalEntities: entities } }))
          .catch((err: unknown) => console.warn('Failed to refresh journal entities', err));
      }
    } catch (e) {
      dispatch({
        type: 'set',
        patch: {
          diceModal: null,
          chatError: e instanceof Error ? e.message : 'Dice roll failed.',
        },
      });
    }
  };

  const handleDiceModalClose = () => {
    dispatch({ type: 'set', patch: { diceModal: null } });
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

  const handleJourneyApply = useCallback(
    async (eventIndex: number) => {
      if (!state.sessionId) return {};
      const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
      return getPlaySessionExtensions(gameId).journeyHandlers.onApply(
        state.sessionId,
        eventIndex,
        dispatch,
        refreshSessionLogs,
      );
    },
    [state.sessionId, state.character?.game_id, dispatch, refreshSessionLogs],
  );

  const handleJourneyDrawItem = useCallback(
    async (eventIndex: number) => {
      if (!state.sessionId) return {};
      const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
      return getPlaySessionExtensions(gameId).journeyHandlers.onDrawItem(
        state.sessionId,
        eventIndex,
        dispatch,
        refreshSessionLogs,
      );
    },
    [state.sessionId, state.character?.game_id, dispatch, refreshSessionLogs],
  );

  const handleJourneyFinish = useCallback(async () => {
    if (!state.sessionId) return;
    const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
    await getPlaySessionExtensions(gameId).journeyHandlers.onFinish(state.sessionId, dispatch, refreshSessionLogs);
  }, [state.sessionId, state.character?.game_id, dispatch, refreshSessionLogs]);

  const handleJourneyDiscard = useCallback(async () => {
    if (!state.sessionId) return;
    const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
    await getPlaySessionExtensions(gameId).journeyHandlers.onDiscard(state.sessionId, dispatch, refreshSessionLogs);
  }, [state.sessionId, state.character?.game_id, dispatch, refreshSessionLogs]);

  const handleJourneyStartCombat = useCallback(
    async (eventIndex: number) => {
      if (!state.sessionId) return;
      const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
      await getPlaySessionExtensions(gameId).journeyHandlers.onStartCombat(
        state.sessionId,
        eventIndex,
        dispatch,
        refreshSessionLogs,
      );
    },
    [state.sessionId, state.character?.game_id, dispatch, refreshSessionLogs],
  );

  const handleDragonkeepAction = useCallback(
    async (action: string) => {
      if (!state.sessionId) return;
      const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
      await getPlaySessionExtensions(gameId).dragonkeepHandlers.onAction(
        state.sessionId,
        action,
        dispatch,
        refreshSessionLogs,
      );
    },
    [state.sessionId, state.character?.game_id, dispatch, refreshSessionLogs],
  );

  const handleDragonkeepInit = useCallback(async () => {
    if (!state.sessionId) return;
    const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
    await getPlaySessionExtensions(gameId).dragonkeepHandlers.onInit(state.sessionId, dispatch);
  }, [state.sessionId, state.character?.game_id, dispatch]);

  const handleBrambletrekCombatAction = useCallback(
    async (action: string, handIndex?: number) => {
      if (!state.sessionId) return;
      const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
      await getPlaySessionExtensions(gameId).combatHandlers.onAction(
        state.sessionId,
        action,
        handIndex,
        dispatch,
        refreshSessionLogs,
      );
    },
    [state.sessionId, state.character?.game_id, dispatch, refreshSessionLogs],
  );

  const handleCombatAction = useCallback(
    async (action: string, targetId?: string) => {
      if (!state.sessionId) return;
      const gameId = state.character?.game_id ?? DEFAULT_GAME_ID;
      await getPlaySessionExtensions(gameId).combatHandlers.onAction(
        state.sessionId,
        action,
        targetId,
        dispatch,
        refreshSessionLogs,
      );
    },
    [state.sessionId, state.character?.game_id, dispatch, refreshSessionLogs],
  );

  return {
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
    handleJourneyApply,
    handleJourneyDrawItem,
    handleJourneyFinish,
    handleJourneyDiscard,
    handleJourneyStartCombat,
    handleDragonkeepAction,
    handleDragonkeepInit,
    handleBrambletrekCombatAction,
    handleCombatAction,
  };
}
