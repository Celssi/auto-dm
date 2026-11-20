import { useCallback, useEffect, useRef, type Dispatch, type MutableRefObject } from 'react';
import { useKeepAlive } from '../../hooks/useKeepAlive';
import { useNavigate } from 'react-router-dom';
import { api, type ChatResult } from '../../api/client';
import type { Character } from '../../types';
import { type DiceModalState, type PlayAction, type PlayState, type SpellCastModalState } from './playState';
import { canCastMagicInitiateFree, listCastableSpells } from '../../components/play/SpellCastModal';
import { getPlaySessionExtensions } from '../../games/brambletrek/playSession';
import { DEFAULT_GAME_ID } from '../../games/registry';
import { getGamePlayConfig } from '../../games/play/registry';
import { useGame } from '../../context/GameContext';
import { bootstrapBrambletrekSession } from '../../games/brambletrek/bootstrapCampaign';

import { initiativeMod } from '../../games/dnd5e/character-sheet/sheetUtils';
import { friendlyDmError } from '../../lib/dmErrors';

const DICE_SHORTCUTS = new Set(['ability_check', 'saving_throw', 'attack_roll', 'initiative', 'death_save']);

function streamErrorDetail(data: unknown): string {
  return friendlyDmError(data);
}

function worldToEntities(world: {
  npcs: { name: string; body: string }[];
  locations: { name: string; body: string }[];
}) {
  return [
    ...world.npcs.map((entry) => ({ kind: 'npc' as const, name: entry.name, body: entry.body })),
    ...world.locations.map((entry) => ({ kind: 'location' as const, name: entry.name, body: entry.body })),
  ];
}

function applyChatResultPatch(result: ChatResult) {
  return {
    ...(result.character ? { character: result.character as Character } : {}),
    sources: result.sources || [],
    spellConfirm: result.spell_confirmation ?? null,
    ...(result.player_progress ? { playerProgress: result.player_progress } : {}),
    adventureComplete: !!result.adventure_complete,
    nextAdventure: result.next_adventure ?? null,
    combatState: result.combat_state && result.combat_state.status === 'active' ? result.combat_state : null,
  };
}

function preferLiveSheet(fetched: Character, streamed: Character | null): Character {
  if (!streamed) return fetched;
  const next = { ...fetched };
  const liveKeys = [
    'hp',
    'max_hp',
    'ac',
    'spell_slots',
    'hit_dice_spent',
    'lay_on_hands_remaining',
    'concentration',
    'active_effects',
    'heroic_inspiration',
    'conditions',
    'inventory',
    'currency',
    'wild_shape_uses',
    'second_wind_remaining',
  ] as const;
  for (const key of liveKeys) {
    if (streamed[key] !== undefined) {
      (next as Record<string, unknown>)[key] = streamed[key];
    }
  }
  next.feature_choices = {
    ...((fetched.feature_choices || {}) as Record<string, unknown>),
    ...((streamed.feature_choices || {}) as Record<string, unknown>),
  };
  return next;
}

function applyBookkeepingStreamEvent(
  event: string,
  sessionId: string,
  dispatch: Dispatch<PlayAction>,
) {
  if (event === 'logs') {
    void Promise.all([api.getLonelog(sessionId), api.getAudit(sessionId)])
      .then(([log, audit]) => {
        dispatch({ type: 'set', patch: { lonelog: log.lines, auditEvents: audit.events } });
      })
      .catch((err: unknown) => console.warn('Failed to refresh logs', err));
  }
  if (event === 'world') {
    void api
      .getSessionWorld(sessionId, true)
      .then((world) => {
        dispatch({
          type: 'set',
          patch: {
            world,
            worldLoading: false,
            worldError: false,
            journalEntities: worldToEntities(world),
          },
        });
      })
      .catch((err: unknown) => console.warn('Failed to refresh session world', err));
  }
}

function applyPlayStreamEvent(
  event: string,
  data: unknown,
  dispatch: Dispatch<PlayAction>,
  done: ChatResult[],
  lastSheet?: MutableRefObject<Character | null>,
): string {
  if (event === 'narration' && typeof data === 'string') {
    dispatch({ type: 'appendAssistantDelta', delta: data });
  } else if (event === 'narration_replace' && typeof data === 'string') {
    return '';
  } else if (event === 'sheet' && data && typeof data === 'object' && 'character' in data) {
    const payload = data as { character?: Character };
    if (payload.character) {
      if (lastSheet) lastSheet.current = payload.character;
      dispatch({ type: 'set', patch: { character: payload.character, sheetUpdating: false } });
    }
  } else if (event === 'ready' && data && typeof data === 'object' && 'response' in data) {
    const payload = data as {
      response?: string;
      character?: Character;
      reaction_prompt?: ChatResult['reaction_prompt'];
    };
    if (payload.response) {
      dispatch({ type: 'replaceLastAssistant', content: payload.response });
    }
    if (payload.character && lastSheet) lastSheet.current = payload.character;
    dispatch({
      type: 'set',
      patch: {
        loading: false,
        sheetUpdating: false,
        ...(payload.character ? { character: payload.character } : {}),
        ...(payload.reaction_prompt ? { reactionPrompt: payload.reaction_prompt } : {}),
      },
    });
  } else if (event === 'done') {
    const result = data as ChatResult;
    done[0] = result;
    dispatch({ type: 'replaceLastAssistant', content: result.response });
    const patch = applyChatResultPatch(result);
    if (patch.character && lastSheet) lastSheet.current = patch.character as Character;
    dispatch({
      type: 'set',
      patch: {
        loading: false,
        sheetUpdating: false,
        ...patch,
        ...(result.reaction_prompt ? { reactionPrompt: result.reaction_prompt } : {}),
      },
    });
  } else if (event === 'error') {
    const message = streamErrorDetail(data);
    dispatch({ type: 'replaceLastAssistant', content: message });
    dispatch({ type: 'set', patch: { loading: false, sheetUpdating: false, chatError: message } });
    return message;
  }
  return '';
}

type QueuedSend = { text: string; shown: boolean };

function chatQueueKey(sessionId: string) {
  return `autodm:chat-queue:${sessionId}`;
}

function readPersistedQueue(sessionId: string): QueuedSend[] {
  if (!sessionId) return [];
  try {
    const raw = sessionStorage.getItem(chatQueueKey(sessionId));
    const parsed = JSON.parse(raw || '[]');
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((row) => ({
        text: String((row as QueuedSend)?.text || '').trim(),
        shown: Boolean((row as QueuedSend)?.shown),
      }))
      .filter((row) => row.text);
  } catch {
    return [];
  }
}

function writePersistedQueue(sessionId: string, items: QueuedSend[]) {
  if (!sessionId) return;
  try {
    if (!items.length) sessionStorage.removeItem(chatQueueKey(sessionId));
    else sessionStorage.setItem(chatQueueKey(sessionId), JSON.stringify(items));
  } catch {
    // quota / private mode
  }
}

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
  const { setGameId } = useGame();
  useKeepAlive(state.loading || state.bootstrapping);
  const inFlightRef = useRef(false);
  const pendingSendsRef = useRef<QueuedSend[]>([]);
  const lastSheetRef = useRef<Character | null>(null);
  const sendMessageRef = useRef<(msg: string, opts?: { alreadyShown?: boolean }) => void>(() => {});
  const restoredQueueRef = useRef('');

  const persistQueue = (sessionId: string) => {
    writePersistedQueue(sessionId, pendingSendsRef.current);
  };

  const enqueueSend = (sessionId: string, item: QueuedSend) => {
    pendingSendsRef.current.push(item);
    persistQueue(sessionId);
  };

  const shiftQueue = (sessionId: string): QueuedSend | undefined => {
    const next = pendingSendsRef.current.shift();
    persistQueue(sessionId);
    return next;
  };

  const refreshSessionLogs = useCallback(
    async (sessionId: string) => {
      const [log, audit] = await Promise.all([api.getLonelog(sessionId), api.getAudit(sessionId)]);
      dispatch({ type: 'set', patch: { lonelog: log.lines, auditEvents: audit.events } });
    },
    [dispatch],
  );

  const loadMeta = useCallback(async () => {
    const [s, c, a, sh, or] = await Promise.all([
      api.listSessions(true),
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

  const loadRecapAndWorld = useCallback(
    async (sessionId: string, messageCount: number, seq: number) => {
      const continuing = messageCount > 0;
      dispatch({
        type: 'set',
        patch: continuing
          ? { recapLoading: true, worldLoading: true, worldError: false }
          : { recapLoading: false, recap: null, worldLoading: true, worldError: false },
      });
      if (continuing) {
        try {
          const recap = await api.getSessionRecap(sessionId);
          if (seq === loadSeqRef.current) {
            dispatch({ type: 'set', patch: { recap, recapLoading: false } });
          }
        } catch (err: unknown) {
          console.warn('Failed to load session recap', err);
          if (seq === loadSeqRef.current) {
            dispatch({ type: 'set', patch: { recapLoading: false } });
          }
        }
      }
      try {
        const world = await api.getSessionWorld(sessionId, continuing);
        if (seq === loadSeqRef.current) {
          dispatch({
            type: 'set',
            patch: {
              world,
              worldLoading: false,
              worldError: false,
              journalEntities: worldToEntities(world),
            },
          });
        }
      } catch (err: unknown) {
        console.warn('Failed to load session world', err);
        if (seq === loadSeqRef.current) {
          dispatch({ type: 'set', patch: { worldLoading: false, worldError: true } });
        }
      }
    },
    [dispatch, loadSeqRef],
  );

  const loadSession = useCallback(
    async (id: string) => {
      if (!id) return;
      const seq = ++loadSeqRef.current;
      dispatch({
        type: 'set',
        patch: { sessionLoaded: false, loadError: '', world: null, worldLoading: true, worldError: false },
      });
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
          const [{ character: ch }, { summary, character: rebuilt }, log, audit] = await fetchCore();
          const gameId = String((ch as Character).game_id || 'dnd5e');
          setGameId(gameId);
          const { shortcuts: sessionShortcuts } = await api.getShortcuts(gameId, session.character_id);
          campaignIdRef.current = '';
          dispatch({
            type: 'set',
            patch: {
              messages: session.messages || [],
              includeFaerun: !!session.include_faerun,
              characterId: session.character_id,
              character: (ch || rebuilt) as Character,
              characterSummary: summary,
              lonelog: log.lines,
              auditEvents: audit.events,
              adventureId: '',
              sessionLoaded: true,
              journalEntities: [],
              recap: null,
              recapLoading: false,
              world: null,
              worldLoading: true,
              campaignId: '',
              playerProgress: null,
              adventureComplete: false,
              nextAdventure: null,
              shortcuts: sessionShortcuts,
            },
          });
          if (gameId) await refreshJourney(id, gameId);
          await loadRecapAndWorld(id, (session.messages || []).length, seq);
          return;
        }

        if (seq !== loadSeqRef.current) return;
        const [[{ character: ch }, { summary, character: rebuilt }, log, audit], adventureResult] = await Promise.all([
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
            character: (ch || rebuilt) as Character,
            characterSummary: summary,
            lonelog: log.lines,
            auditEvents: audit.events,
            adventureId: session.adventure_id,
            sessionLoaded: true,
            journalEntities,
            world: {
              npcs: journalEntities.filter((row) => row.kind === 'npc'),
              locations: journalEntities.filter((row) => row.kind === 'location'),
              message_count: (session.messages || []).length,
            },
            worldLoading: true,
            campaignId,
            playerProgress,
            adventureComplete,
            nextAdventure: null,
            shortcuts: (await api.getShortcuts(String((ch as Character).game_id || 'dnd5e'), session.character_id))
              .shortcuts,
          },
        });
        const loadedGameId = String((ch as Character).game_id || 'dnd5e');
        setGameId(loadedGameId);
        if (loadedGameId) await refreshJourney(id, loadedGameId);
        await loadRecapAndWorld(id, (session.messages || []).length, seq);
      } catch (e) {
        if (seq !== loadSeqRef.current) return;
        dispatch({
          type: 'set',
          patch: {
            sessionLoaded: true,
            worldLoading: false,
            loadError: e instanceof Error ? e.message : 'Failed to load session',
          },
        });
      }
    },
    [dispatch, loadSeqRef, campaignIdRef, refreshJourney, setGameId, loadRecapAndWorld],
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
        patch: { bootstrapError: friendlyDmError(e instanceof Error ? e.message : e) },
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

  const sendMessage = async (msg: string, opts?: { alreadyShown?: boolean }) => {
    const { sessionId } = state;
    if (!sessionId || !msg.trim()) return;
    const text = msg.trim();
    if (inFlightRef.current) {
      if (!opts?.alreadyShown) {
        dispatch({ type: 'appendMessages', messages: [{ role: 'user', content: text }] });
      }
      enqueueSend(sessionId, { text, shown: true });
      dispatch({ type: 'set', patch: { input: '', queuedCount: pendingSendsRef.current.length } });
      return;
    }
    inFlightRef.current = true;
    dispatch({ type: 'set', patch: { input: '', spellConfirm: null, reactionPrompt: null, chatError: '' } });
    if (!opts?.alreadyShown) {
      dispatch({ type: 'appendMessages', messages: [{ role: 'user', content: text }] });
    }
    dispatch({ type: 'set', patch: { loading: true } });
    dispatch({ type: 'appendMessages', messages: [{ role: 'assistant', content: '' }] });
    try {
      const done: ChatResult[] = [];
      let streamError = '';
      await api.chatStream(sessionId, text, (event, data) => {
        applyBookkeepingStreamEvent(event, sessionId, dispatch);
        const err = applyPlayStreamEvent(event, data, dispatch, done, lastSheetRef);
        if (err) streamError = err;
      });
      if (streamError) throw new Error(streamError);
      const result = done[0];
      if (!result) throw new Error('The DM closed the stream without a reply.');
      void refreshSessionLogs(sessionId);
      if (state.characterId) {
        api
          .getCharacter(state.characterId)
          .then((fresh) => {
            const sheet = preferLiveSheet(fresh.character as Character, lastSheetRef.current);
            lastSheetRef.current = sheet;
            dispatch({ type: 'set', patch: { character: sheet } });
          })
          .catch((err: unknown) => console.warn('Failed to refresh character after chat', err));
      }
      const chatGameId = String((result.character as Character)?.game_id || state.character?.game_id || 'dnd5e');
      void getPlaySessionExtensions(chatGameId).afterChat(sessionId, dispatch);
      api
        .getSessionWorld(sessionId, false)
        .then((world) =>
          dispatch({
            type: 'set',
            patch: {
              world,
              journalEntities: worldToEntities(world),
            },
          }),
        )
        .catch((err: unknown) => {
          console.warn('Failed to refresh session world', err);
          if (campaignIdRef.current) {
            api
              .getCampaignEntities(campaignIdRef.current)
              .then(({ entities }) => dispatch({ type: 'set', patch: { journalEntities: entities } }))
              .catch((inner: unknown) => console.warn('Failed to refresh journal entities', inner));
          }
        });
    } catch (e) {
      const message = friendlyDmError(e instanceof Error ? e.message : e);
      dispatch({ type: 'replaceLastAssistant', content: message });
      dispatch({
        type: 'set',
        patch: { chatError: message },
      });
    } finally {
      inFlightRef.current = false;
      dispatch({
        type: 'set',
        patch: { loading: false, sheetUpdating: false, queuedCount: pendingSendsRef.current.length },
      });
      const next = state.sessionId ? shiftQueue(sessionId) : pendingSendsRef.current.shift();
      if (next) {
        dispatch({ type: 'set', patch: { queuedCount: pendingSendsRef.current.length } });
        void sendMessage(next.text, { alreadyShown: next.shown });
      }
    }
  };

  sendMessageRef.current = sendMessage;

  useEffect(() => {
    const sessionId = state.sessionId;
    if (!state.sessionLoaded || !sessionId) return;
    if (restoredQueueRef.current === sessionId) return;
    restoredQueueRef.current = sessionId;
    const queued = readPersistedQueue(sessionId);
    if (!queued.length) return;
    pendingSendsRef.current = queued;
    dispatch({ type: 'set', patch: { queuedCount: queued.length } });
    if (inFlightRef.current) return;
    const next = shiftQueue(sessionId);
    if (!next) return;
    dispatch({ type: 'set', patch: { queuedCount: pendingSendsRef.current.length } });
    void sendMessageRef.current(next.text, { alreadyShown: false });
  }, [state.sessionLoaded, state.sessionId, dispatch]);

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
    if (id === 'cast_spell') {
      if (!state.sessionLoaded || !state.character) {
        dispatch({
          type: 'set',
          patch: { chatError: 'Wait for the character sheet to finish loading before casting.' },
        });
        return;
      }
      const spells = listCastableSpells(state.character);
      if (!spells.length) {
        dispatch({
          type: 'set',
          patch: { chatError: 'No prepared or Magic Initiate spells are loaded yet.' },
        });
        return;
      }
      const first = spells[0];
      const modal: SpellCastModalState = {
        spellName: first?.name || '',
        slotLevel: first?.cantrip ? 0 : 1,
        freeUse: canCastMagicInitiateFree(state.character, first?.name || ''),
        ritual: false,
        submitting: false,
      };
      dispatch({ type: 'set', patch: { spellCastModal: modal } });
      return;
    }
    if (!DICE_SHORTCUTS.has(id) || !state.character) {
      if (id === 'cast_spell') return;
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
    inFlightRef.current = true;

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
      type ShortcutPayload = { dice?: { rolls?: number[]; total?: number }; user_message?: string };
      const shortcutBox: ShortcutPayload[] = [];
      const done: ChatResult[] = [];
      let streamError = '';
      let resolveShortcut: (value: ShortcutPayload) => void = () => undefined;
      const shortcutReady = new Promise<ShortcutPayload>((resolve) => {
        resolveShortcut = resolve;
      });
      const pending: { event: string; data: unknown }[] = [];
      let uiReady = false;

      const applyEvent = (event: string, data: unknown) => {
        applyBookkeepingStreamEvent(event, state.sessionId, dispatch);
        const err = applyPlayStreamEvent(event, data, dispatch, done, lastSheetRef);
        if (err) streamError = err;
        if (event === 'ready' || event === 'done') {
          dispatch({ type: 'set', patch: { diceModal: null } });
        }
      };

      const streamPromise = api.rollShortcutStream(
        state.sessionId,
        modal.shortcutId,
        params,
        preRolled,
        (event, data) => {
          if (event === 'shortcut') {
            const payload = data as ShortcutPayload;
            shortcutBox[0] = payload;
            resolveShortcut(payload);
            return;
          }
          if (!uiReady) {
            pending.push({ event, data });
            return;
          }
          applyEvent(event, data);
        },
      );

      const shortcutPayload = await Promise.race([
        shortcutReady,
        streamPromise.then(() => {
          const payload = shortcutBox[0];
          if (!payload) {
            throw new Error(streamError || 'Dice shortcut stream ended before the roll.');
          }
          return payload;
        }),
      ]);

      const rolls = shortcutPayload.dice?.rolls;
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

      const userMsg = shortcutPayload.user_message ?? `/${modal.shortcutId}`;
      dispatch({
        type: 'appendMessages',
        messages: [
          { role: 'user', content: userMsg },
          { role: 'assistant', content: '' },
        ],
      });
      uiReady = true;
      for (const item of pending) {
        applyEvent(item.event, item.data);
      }
      await streamPromise;
      if (streamError) throw new Error(streamError);
      if (!done[0]) throw new Error('The DM closed the stream without a reply.');
      void refreshSessionLogs(state.sessionId);
      if (state.characterId) {
        api
          .getCharacter(state.characterId)
          .then((fresh) => {
            dispatch({
              type: 'set',
              patch: { character: preferLiveSheet(fresh.character as Character, lastSheetRef.current) },
            });
          })
          .catch((err: unknown) => console.warn('Failed to refresh character after dice shortcut', err));
      }
      api
        .getSessionWorld(state.sessionId, false)
        .then((world) =>
          dispatch({
            type: 'set',
            patch: {
              world,
              journalEntities: worldToEntities(world),
            },
          }),
        )
        .catch((err: unknown) => {
          console.warn('Failed to refresh session world', err);
          if (campaignIdRef.current) {
            api
              .getCampaignEntities(campaignIdRef.current)
              .then(({ entities }) => dispatch({ type: 'set', patch: { journalEntities: entities } }))
              .catch((inner: unknown) => console.warn('Failed to refresh journal entities', inner));
          }
        });
    } catch (e) {
      const message = friendlyDmError(e instanceof Error ? e.message : e);
      dispatch({
        type: 'set',
        patch: {
          diceModal: null,
          chatError: message,
        },
      });
    } finally {
      inFlightRef.current = false;
      dispatch({ type: 'set', patch: { queuedCount: pendingSendsRef.current.length } });
      const next = state.sessionId ? shiftQueue(state.sessionId) : pendingSendsRef.current.shift();
      if (next) {
        dispatch({ type: 'set', patch: { queuedCount: pendingSendsRef.current.length } });
        void sendMessage(next.text, { alreadyShown: next.shown });
      }
    }
  };

  const handleDiceModalClose = () => {
    dispatch({ type: 'set', patch: { diceModal: null } });
  };

  const handleSpellCastModalUpdate = (patch: Partial<SpellCastModalState>) => {
    if (!state.spellCastModal) return;
    dispatch({ type: 'set', patch: { spellCastModal: { ...state.spellCastModal, ...patch } } });
  };

  const handleSpellCastModalClose = () => {
    dispatch({ type: 'set', patch: { spellCastModal: null } });
  };

  const handleSpellCastModalSubmit = async () => {
    const modal = state.spellCastModal;
    if (!modal || !state.sessionId || !modal.spellName.trim()) return;
    inFlightRef.current = true;
    dispatch({ type: 'set', patch: { spellCastModal: { ...modal, submitting: true }, chatError: '' } });
    try {
      const done: ChatResult[] = [];
      let streamError = '';
      dispatch({ type: 'set', patch: { loading: true, spellCastModal: null } });
      dispatch({
        type: 'appendMessages',
        messages: [
          {
            role: 'user',
            content: `**Cast spell**\n\n${modal.spellName}${modal.freeUse ? ' (Magic Initiate free)' : ''}`,
          },
          { role: 'assistant', content: '' },
        ],
      });
      await api.rollShortcutStream(
        state.sessionId,
        'cast_spell',
        {
          spell_name: modal.spellName,
          slot_level: modal.slotLevel,
          free_use: modal.freeUse,
          ritual: modal.ritual,
          requested_text: modal.freeUse ? `${modal.spellName} Magic Initiate free` : modal.spellName,
        },
        undefined,
        (event, data) => {
          applyBookkeepingStreamEvent(event, state.sessionId, dispatch);
          const err = applyPlayStreamEvent(event, data, dispatch, done, lastSheetRef);
          if (err) streamError = err;
        },
      );
      if (streamError) throw new Error(streamError);
      if (!done[0]) throw new Error('The DM closed the stream without a reply.');
      void refreshSessionLogs(state.sessionId);
      if (state.characterId) {
        api
          .getCharacter(state.characterId)
          .then((fresh) => {
            dispatch({
              type: 'set',
              patch: { character: preferLiveSheet(fresh.character as Character, lastSheetRef.current) },
            });
          })
          .catch((err: unknown) => console.warn('Failed to refresh character after spell cast', err));
      }
    } catch (e) {
      const message = friendlyDmError(e instanceof Error ? e.message : e);
      dispatch({
        type: 'set',
        patch: {
          spellCastModal: null,
          chatError: message,
        },
      });
    } finally {
      inFlightRef.current = false;
      dispatch({
        type: 'set',
        patch: { loading: false, sheetUpdating: false, queuedCount: pendingSendsRef.current.length },
      });
      const next = state.sessionId ? shiftQueue(state.sessionId) : pendingSendsRef.current.shift();
      if (next) {
        dispatch({ type: 'set', patch: { queuedCount: pendingSendsRef.current.length } });
        void sendMessage(next.text, { alreadyShown: next.shown });
      }
    }
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

  const renameSession = async (id: string, name: string) => {
    await api.updateSession(id, { name });
    await loadMeta();
  };

  const archiveSession = async (id: string, archived: boolean) => {
    await api.updateSession(id, { archived });
    await loadMeta();
  };

  const toggleHeroicInspiration = useCallback(
    async (next: boolean) => {
      if (!state.characterId || !state.character) return;
      const optimistic = { ...state.character, heroic_inspiration: next };
      lastSheetRef.current = optimistic;
      dispatch({ type: 'set', patch: { character: optimistic } });
      try {
        const res = await api.patchLiveCharacter(state.characterId, { heroic_inspiration: next });
        const sheet = preferLiveSheet(res.character as Character, lastSheetRef.current);
        lastSheetRef.current = sheet;
        dispatch({ type: 'set', patch: { character: sheet } });
      } catch (err: unknown) {
        console.warn('Failed to toggle Heroic Inspiration', err);
      }
    },
    [dispatch, state.character, state.characterId],
  );

  const rebuildSheet = useCallback(async () => {
    if (!state.characterId) return;
    try {
      const { character: rebuilt } = await api.rebuildCharacter(state.characterId);
      lastSheetRef.current = rebuilt as Character;
      dispatch({ type: 'set', patch: { character: rebuilt as Character } });
    } catch (err: unknown) {
      console.warn('Failed to rebuild character sheet', err);
    }
  }, [dispatch, state.characterId]);

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
  };
}
