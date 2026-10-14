import { useCallback, useEffect, useRef, type Dispatch, type SetStateAction } from 'react';
import type { NavigateFunction } from 'react-router-dom';
import { api } from '../../api/client';
import type { Character } from '../../types';
import { DEFAULT_GAME_ID } from '../../games/registry';
import type { CharactersAction, CharactersState } from './charactersState';
import { useToast } from '../../components/ui/toast';
import { rosterEntryFromCharacter } from '../../lib/displayText';

export type SaveCharOptions = { silentToast?: boolean; alreadyPersisted?: boolean };

export function useCharactersPageActions(
  state: CharactersState,
  dispatch: Dispatch<CharactersAction>,
  characterId: string | undefined,
  activeGameId: string,
  navigate: NavigateFunction,
  setDeleting: (value: boolean) => void,
  setConfirmDelete: Dispatch<SetStateAction<boolean>>,
  setCreatingImmediate: Dispatch<SetStateAction<boolean>>,
) {
  const toast = useToast();
  const activeIdRef = useRef(state.activeId);
  useEffect(() => {
    activeIdRef.current = state.activeId;
  }, [state.activeId]);

  const load = useCallback(async () => {
    const { characters } = await api.listCharacters();
    const roster = await Promise.all(
      characters.map(async (entry) => {
        try {
          const { character } = await api.getCharacter(entry.id);
          return rosterEntryFromCharacter(entry.id, entry.name, character);
        } catch {
          return entry;
        }
      }),
    );
    dispatch({ type: 'set', patch: { roster, rosterLoaded: true, error: null } });
  }, [dispatch]);

  const loadCharacter = useCallback(
    async (id: string) => {
      const [{ character: c }, sum] = await Promise.all([api.getCharacter(id), api.getCharacterSummary(id)]);
      dispatch({
        type: 'set',
        patch: { character: c as Character, summary: sum.summary, activeId: id, error: null },
      });
    },
    [dispatch],
  );

  const saveChar = useCallback(
    async (c: Character, opts?: SaveCharOptions) => {
      await persistCharacter({
        character: c,
        opts,
        activeId: activeIdRef.current,
        characterId,
        newGameId: activeGameId,
        dispatch,
        load,
        navigate,
        toast,
      });
    },
    [characterId, activeGameId, dispatch, load, navigate, toast],
  );

  const startImmediateCharacter = useCallback(
    async (targetGameId: string) => {
      setCreatingImmediate(true);
      dispatch({ type: 'set', patch: { error: null } });
      try {
        const res = await api.createCharacter({ game_id: targetGameId, name: '' });
        await load();
        navigate(`/characters/${res.id}/edit`, { replace: true });
      } catch (e) {
        reportError(e, 'Failed to create character', dispatch, toast);
      } finally {
        setCreatingImmediate(false);
      }
    },
    [dispatch, load, navigate, setCreatingImmediate, toast],
  );

  const levelUp = useCallback(
    async (
      hpRoll: number | undefined,
      asiChoices: Record<string, unknown>[],
      className?: string,
      spells?: { cantrips?: string[]; prepared_spells?: string[]; known_spells?: string[] },
      choices?: Partial<Character>,
    ) => {
      const id = activeIdRef.current || characterId;
      if (!id) return;
      try {
        const res = await api.levelUpCharacter(id, levelUpPayload(hpRoll, asiChoices, className, spells, choices));
        dispatch({
          type: 'set',
          patch: { character: res.character as Character, summary: res.summary, levelUpOpen: false },
        });
        toast.success('Character leveled up');
      } catch (e) {
        reportError(e, 'Level up failed', dispatch, toast);
      }
    },
    [characterId, dispatch, toast],
  );

  const deleteCharacter = useCallback(
    async (character: Character | null) => {
      const id = activeIdRef.current || characterId;
      if (!id || !character) return;
      setDeleting(true);
      dispatch({ type: 'set', patch: { error: null } });
      try {
        await api.deleteCharacter(id);
        setConfirmDelete(false);
        dispatch({ type: 'set', patch: { activeId: null, character: null } });
        await load();
        navigate('/characters');
        toast.success(`Deleted ${character.name || 'character'}`);
      } catch (e) {
        reportError(e, 'Delete failed', dispatch, toast);
      } finally {
        setDeleting(false);
      }
    },
    [characterId, dispatch, load, navigate, setConfirmDelete, setDeleting, toast],
  );

  return { load, loadCharacter, saveChar, startImmediateCharacter, levelUp, deleteCharacter };
}

function reportError(
  e: unknown,
  fallback: string,
  dispatch: Dispatch<CharactersAction>,
  toast: { error: (msg: string) => void },
) {
  const msg = e instanceof Error ? e.message : fallback;
  toast.error(msg);
  dispatch({ type: 'set', patch: { error: msg } });
}

async function persistCharacter({
  character,
  opts,
  activeId,
  characterId,
  newGameId,
  dispatch,
  load,
  navigate,
  toast,
}: {
  character: Character;
  opts?: SaveCharOptions;
  activeId: string | null;
  characterId: string | undefined;
  newGameId: string | null;
  dispatch: Dispatch<CharactersAction>;
  load: () => Promise<void>;
  navigate: NavigateFunction;
  toast: { success: (msg: string) => void; error: (msg: string) => void };
}) {
  let id = activeId || characterId || null;
  try {
    if (!opts?.alreadyPersisted) {
      if (id) {
        await api.updateCharacter(id, character as Record<string, unknown>);
      } else {
        const res = await api.createCharacter({
          ...(character as Record<string, unknown>),
          game_id: character.game_id || newGameId || DEFAULT_GAME_ID,
        });
        id = res.id;
        dispatch({ type: 'set', patch: { activeId: res.id, character: res.character as Character } });
      }
    }
    await load();
    if (!id) return;
    const sum = await api.getCharacterSummary(id);
    dispatch({ type: 'set', patch: { summary: sum.summary, character: sum.character as Character } });
    if (!opts?.silentToast) {
      const name = String(character.name || sum.character?.name || '').trim() || 'Character';
      toast.success(`Saved ${name}`);
    }
    navigate(`/characters/${id}`);
  } catch (e) {
    reportError(e, 'Save failed', dispatch, toast);
    throw e;
  }
}

function levelUpPayload(
  hpRoll: number | undefined,
  asiChoices: Record<string, unknown>[],
  className?: string,
  spells?: { cantrips?: string[]; prepared_spells?: string[]; known_spells?: string[] },
  choices?: Partial<Character>,
) {
  return {
    hp_roll: hpRoll,
    asi_choices: asiChoices,
    class_name: className,
    ...spells,
    ...(choices?.feature_choices ? { feature_choices: choices.feature_choices as Record<string, unknown> } : {}),
    ...(choices?.fighting_style_feat ? { fighting_style_feat: choices.fighting_style_feat } : {}),
    ...(choices?.weapon_mastery ? { weapon_mastery: choices.weapon_mastery } : {}),
    ...(typeof choices?.human_skill === 'string' && choices.human_skill ? { human_skill: choices.human_skill } : {}),
    ...(choices?.versatile_origin_feat ? { versatile_origin_feat: choices.versatile_origin_feat } : {}),
  };
}
