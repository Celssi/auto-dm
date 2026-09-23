import type { Dispatch } from 'react';
import { api } from '../../api/client';
import type { Character } from '../../types';
import type { PlayAction } from '../../pages/play/playState';

type DispatchFn = Dispatch<PlayAction>;
type RefreshLogs = (sessionId: string) => Promise<void>;

export interface PlaySessionExtensions {
  refreshJourney: (sessionId: string, dispatch: DispatchFn) => Promise<void>;
  refreshDragonkeep: (sessionId: string, dispatch: DispatchFn) => Promise<void>;
  afterChat: (sessionId: string, dispatch: DispatchFn) => Promise<void>;
  afterLoadSession: (sessionId: string, gameId: string, dispatch: DispatchFn) => Promise<void>;
  runShortcut: (
    sessionId: string,
    id: string,
    dispatch: DispatchFn,
    refreshSessionLogs: RefreshLogs,
  ) => Promise<boolean>;
  journeyHandlers: {
    onApply: (
      sessionId: string,
      eventIndex: number,
      dispatch: DispatchFn,
      refreshSessionLogs: RefreshLogs,
    ) => Promise<{ summary?: string; item_error?: string | null }>;
    onDrawItem: (
      sessionId: string,
      eventIndex: number,
      dispatch: DispatchFn,
      refreshSessionLogs: RefreshLogs,
    ) => Promise<{ item_error?: string | null }>;
    onFinish: (sessionId: string, dispatch: DispatchFn, refreshSessionLogs: RefreshLogs) => Promise<void>;
    onDiscard: (sessionId: string, dispatch: DispatchFn, refreshSessionLogs: RefreshLogs) => Promise<void>;
    onStartCombat: (
      sessionId: string,
      eventIndex: number,
      dispatch: DispatchFn,
      refreshSessionLogs: RefreshLogs,
    ) => Promise<void>;
  };
  dragonkeepHandlers: {
    onAction: (
      sessionId: string,
      action: string,
      dispatch: DispatchFn,
      refreshSessionLogs: RefreshLogs,
    ) => Promise<void>;
    onInit: (sessionId: string, dispatch: DispatchFn) => Promise<void>;
  };
  combatHandlers: {
    onAction: (
      sessionId: string,
      action: string,
      handIndex: number | undefined,
      dispatch: DispatchFn,
      refreshSessionLogs: RefreshLogs,
    ) => Promise<void>;
  };
}

const noopExtensions: PlaySessionExtensions = {
  refreshJourney: async () => {},
  refreshDragonkeep: async () => {},
  afterChat: async () => {},
  afterLoadSession: async () => {},
  runShortcut: async () => false,
  journeyHandlers: {
    onApply: async () => ({}),
    onDrawItem: async () => ({}),
    onFinish: async () => {},
    onDiscard: async () => {},
    onStartCombat: async () => {},
  },
  dragonkeepHandlers: {
    onAction: async () => {},
    onInit: async () => {},
  },
  combatHandlers: {
    onAction: async () => {},
  },
};

async function refreshJourney(sessionId: string, dispatch: DispatchFn) {
  try {
    const { pending_journey } = await api.brambletrekGetJourney(sessionId);
    dispatch({ type: 'set', patch: { pendingJourney: pending_journey } });
  } catch {
    dispatch({ type: 'set', patch: { pendingJourney: null } });
  }
}

async function refreshDragonkeep(sessionId: string, dispatch: DispatchFn) {
  try {
    const res = await api.brambletrekGetDragonkeep(sessionId);
    dispatch({
      type: 'set',
      patch: {
        dragonkeep: res.dragonkeep ?? null,
        pendingJourney: res.pending_journey ?? null,
      },
    });
  } catch {
    dispatch({ type: 'set', patch: { dragonkeep: null } });
  }
}

async function refreshCombat(sessionId: string, dispatch: DispatchFn) {
  try {
    const { combat } = await api.brambletrekGetCombat(sessionId);
    dispatch({
      type: 'set',
      patch: { brambletrekCombat: combat?.status && combat.status !== 'idle' ? combat : null },
    });
  } catch {
    dispatch({ type: 'set', patch: { brambletrekCombat: null } });
  }
}

const brambletrekExtensions: PlaySessionExtensions = {
  refreshJourney,
  refreshDragonkeep,
  afterChat: async (sessionId, dispatch) => {
    await Promise.all([
      refreshJourney(sessionId, dispatch),
      refreshDragonkeep(sessionId, dispatch),
      refreshCombat(sessionId, dispatch),
    ]);
  },
  afterLoadSession: async (sessionId, gameId, dispatch) => {
    const tasks = [refreshJourney(sessionId, dispatch)];
    if (gameId === 'brambletrek') {
      tasks.push(refreshDragonkeep(sessionId, dispatch), refreshCombat(sessionId, dispatch));
    }
    await Promise.all(tasks);
  },
  async runShortcut(sessionId, id, dispatch, refreshSessionLogs) {
    dispatch({ type: 'set', patch: { loading: true, chatError: '' } });
    try {
      const result = await api.rollShortcut(sessionId, id, {});
      const userLine = result.shortcut?.user_message || `Shortcut: ${id}`;
      dispatch({
        type: 'appendMessages',
        messages: [
          { role: 'user', content: userLine },
          { role: 'assistant', content: result.response },
        ],
      });
      dispatch({
        type: 'set',
        patch: {
          character: result.character as Character,
          sources: result.sources || [],
        },
      });
      await Promise.all([
        refreshSessionLogs(sessionId),
        refreshJourney(sessionId, dispatch),
        refreshDragonkeep(sessionId, dispatch),
      ]);
      return true;
    } catch (e) {
      dispatch({
        type: 'set',
        patch: { chatError: e instanceof Error ? e.message : 'Shortcut failed' },
      });
      return true;
    } finally {
      dispatch({ type: 'set', patch: { loading: false } });
    }
  },
  journeyHandlers: {
    async onApply(sessionId, eventIndex, dispatch, refreshSessionLogs) {
      const res = await api.brambletrekApplyJourney(sessionId, eventIndex);
      dispatch({
        type: 'set',
        patch: {
          ...(res.character ? { character: res.character as Character } : {}),
          pendingJourney: res.pending_journey ?? null,
        },
      });
      await refreshSessionLogs(sessionId);
      return { summary: res.summary, item_error: res.item_error };
    },
    async onDrawItem(sessionId, eventIndex, dispatch, refreshSessionLogs) {
      const res = await api.brambletrekDrawJourneyItem(sessionId, eventIndex);
      dispatch({
        type: 'set',
        patch: {
          ...(res.character ? { character: res.character as Character } : {}),
          pendingJourney: res.pending_journey ?? null,
        },
      });
      await refreshSessionLogs(sessionId);
      return { item_error: res.item_error };
    },
    async onFinish(sessionId, dispatch, refreshSessionLogs) {
      const res = await api.brambletrekFinishJourney(sessionId);
      dispatch({
        type: 'set',
        patch: {
          ...(res.character ? { character: res.character as Character } : {}),
          pendingJourney: null,
          ...(res.dragonkeep ? { dragonkeep: res.dragonkeep } : {}),
        },
      });
      await refreshSessionLogs(sessionId);
      await refreshDragonkeep(sessionId, dispatch);
    },
    async onDiscard(sessionId, dispatch, refreshSessionLogs) {
      await api.brambletrekDiscardJourney(sessionId);
      dispatch({ type: 'set', patch: { pendingJourney: null } });
      await refreshSessionLogs(sessionId);
      await refreshDragonkeep(sessionId, dispatch);
    },
    async onStartCombat(sessionId, eventIndex, dispatch, refreshSessionLogs) {
      const res = await api.brambletrekStartJourneyCombat(sessionId, eventIndex);
      dispatch({
        type: 'set',
        patch: {
          pendingJourney: res.pending_journey ?? null,
          ...(res.dragonkeep ? { dragonkeep: res.dragonkeep } : {}),
          brambletrekCombat: res.combat?.status === 'active' ? res.combat : null,
        },
      });
      await refreshSessionLogs(sessionId);
      await refreshDragonkeep(sessionId, dispatch);
    },
  },
  dragonkeepHandlers: {
    async onInit(sessionId, dispatch) {
      const res = await api.brambletrekInitDragonkeep(sessionId);
      dispatch({
        type: 'set',
        patch: {
          dragonkeep: res.dragonkeep,
          pendingJourney: res.pending_journey ?? null,
        },
      });
    },
    async onAction(sessionId, action, dispatch, refreshSessionLogs) {
      const res = await api.brambletrekDragonkeepAction(sessionId, action);
      dispatch({
        type: 'set',
        patch: {
          dragonkeep: res.dragonkeep,
          pendingJourney: res.pending_journey ?? null,
          ...(res.character ? { character: res.character as Character } : {}),
          ...(res.combat?.status === 'active' ? { brambletrekCombat: res.combat } : {}),
        },
      });
      await refreshSessionLogs(sessionId);
    },
  },
  combatHandlers: {
    async onAction(sessionId, action, handIndex, dispatch, refreshSessionLogs) {
      const res = await api.brambletrekCombatAction(sessionId, action, handIndex ?? -1);
      dispatch({
        type: 'set',
        patch: {
          brambletrekCombat: res.combat?.status === 'active' ? res.combat : (res.combat ?? null),
          ...(res.character ? { character: res.character as Character } : {}),
          ...(res.dragonkeep ? { dragonkeep: res.dragonkeep } : {}),
        },
      });
      await refreshSessionLogs(sessionId);
    },
  },
};

const EXTENSIONS: Record<string, PlaySessionExtensions> = {
  brambletrek: brambletrekExtensions,
  dnd5e: {
    ...noopExtensions,
    afterChat: async (sessionId, dispatch) => {
      try {
        const { combat_state } = await api.getSessionCombat(sessionId);
        dispatch({
          type: 'set',
          patch: {
            combatState: combat_state?.status === 'active' ? combat_state : null,
          },
        });
      } catch {
        /* optional */
      }
    },
    combatHandlers: {
      onAction: async (sessionId, action, targetId, dispatch, refreshSessionLogs) => {
        const res = await api.sessionCombatAction(sessionId, {
          action,
          target_id: targetId,
        });
        if (res.combat_state) {
          dispatch({
            type: 'set',
            patch: {
              combatState: res.combat_state.status === 'active' ? res.combat_state : null,
            },
          });
        }
        if (res.character) {
          dispatch({ type: 'set', patch: { character: res.character } });
        }
        await refreshSessionLogs(sessionId);
      },
    },
  },
};

export function getPlaySessionExtensions(gameId: string | undefined): PlaySessionExtensions {
  return EXTENSIONS[gameId ?? 'dnd5e'] ?? noopExtensions;
}
