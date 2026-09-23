import { useCallback, useEffect, useReducer, useState } from 'react';
import { useMatch, useNavigate, useParams } from 'react-router-dom';
import { m } from '../lib/framer';
import { UserPlus, Users } from 'lucide-react';
import { api } from '../api/client';
import type { Character } from '../types';
import { DEFAULT_GAME_ID, GAMES, gameLabel, getGameCharacterConfig } from '../games/registry';
import { GameCharacterSetup, GameCharacterWizard } from '../games/components';
import LevelUpDialog from '../games/dnd5e/character-sheet/LevelUpDialog';
import PageHeader from '../components/ui/PageHeader';
import ListCard from '../components/ui/ListCard';
import EmptyState from '../components/ui/EmptyState';
import ListLoading from '../components/ui/ListLoading';
import AnimatedPage from '../components/ui/AnimatedPage';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { fadeUp, staggerContainer } from '../components/ui/motion';
import CharacterDetailPanel from './characters/CharacterDetailPanel';
import { charactersReducer, initialCharactersState } from './characters/charactersState';
import { useToast } from '../components/ui/toast';

type SaveCharOptions = { silentToast?: boolean; alreadyPersisted?: boolean };

export default function CharactersPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { characterId } = useParams();
  const isNew = useMatch('/characters/new');
  const isEdit = useMatch('/characters/:characterId/edit');
  const mode = isNew || isEdit ? 'wizard' : characterId ? 'view' : 'list';

  const [state, dispatch] = useReducer(charactersReducer, initialCharactersState);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [charOptions, setCharOptions] = useState<Record<string, unknown>>({});
  const [newGameId, setNewGameId] = useState<string | null>(null);
  const [creatingImmediate, setCreatingImmediate] = useState(false);

  const load = useCallback(async () => {
    const { characters } = await api.listCharacters();
    dispatch({ type: 'set', patch: { roster: characters, rosterLoaded: true } });
  }, []);

  const loadCharacter = useCallback(async (id: string) => {
    const [{ character: c }, sum] = await Promise.all([api.getCharacter(id), api.getCharacterSummary(id)]);
    dispatch({
      type: 'set',
      patch: { character: c as Character, summary: sum.summary, activeId: id, error: null },
    });
  }, []);

  useEffect(() => {
    load().catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [load]);

  useEffect(() => {
    if (mode !== 'view' && mode !== 'wizard') {
      dispatch({ type: 'set', patch: { character: null, activeId: null, summary: {} } });
      return;
    }
    if (!characterId || isNew) return;
    loadCharacter(characterId).catch(() => {
      dispatch({ type: 'set', patch: { error: 'Character not found.', character: null, activeId: null } });
    });
  }, [characterId, isNew, mode, loadCharacter]);

  useEffect(() => {
    if (mode !== 'view' && mode !== 'wizard') return;
    if (!characterId || isNew) return;
    const gid = state.character?.game_id || DEFAULT_GAME_ID;
    api
      .getCharacterOptions(false, gid)
      .then(setCharOptions)
      .catch(() => setCharOptions({}));
  }, [mode, characterId, isNew, state.character?.game_id]);

  const saveChar = async (c: Character, opts?: SaveCharOptions) => {
    let id = state.activeId || characterId || null;
    try {
      if (!opts?.alreadyPersisted) {
        if (id) {
          await api.updateCharacter(id, c as Record<string, unknown>);
        } else {
          const res = await api.createCharacter({
            ...(c as Record<string, unknown>),
            game_id: c.game_id || newGameId || DEFAULT_GAME_ID,
          });
          id = res.id;
          dispatch({ type: 'set', patch: { activeId: res.id, character: res.character as Character } });
        }
      }
      await load();
      if (id) {
        const sum = await api.getCharacterSummary(id);
        dispatch({ type: 'set', patch: { summary: sum.summary, character: sum.character as Character } });
        if (!opts?.silentToast) {
          const name = String(c.name || sum.character?.name || '').trim() || 'Character';
          toast.success(`Saved ${name}`);
        }
        navigate(`/characters/${id}`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Save failed';
      toast.error(msg);
      dispatch({ type: 'set', patch: { error: msg } });
      throw e;
    }
  };

  const startImmediateCharacter = async (targetGameId: string) => {
    setCreatingImmediate(true);
    dispatch({ type: 'set', patch: { error: null } });
    try {
      const res = await api.createCharacter({ game_id: targetGameId, name: '' });
      await load();
      navigate(`/characters/${res.id}/edit`, { replace: true });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to create character';
      toast.error(msg);
      dispatch({ type: 'set', patch: { error: msg } });
    } finally {
      setCreatingImmediate(false);
    }
  };

  const levelUp = async (
    hpRoll: number | undefined,
    asiChoices: Record<string, unknown>[],
    className?: string,
    spells?: { cantrips?: string[]; prepared_spells?: string[]; known_spells?: string[] },
    choices?: Partial<Character>,
  ) => {
    const id = state.activeId || characterId;
    if (!id) return;
    try {
      const res = await api.levelUpCharacter(id, {
      hp_roll: hpRoll,
      asi_choices: asiChoices,
      class_name: className,
      ...spells,
      ...(choices?.feature_choices ? { feature_choices: choices.feature_choices as Record<string, unknown> } : {}),
      ...(choices?.fighting_style_feat ? { fighting_style_feat: choices.fighting_style_feat } : {}),
      ...(choices?.weapon_mastery ? { weapon_mastery: choices.weapon_mastery } : {}),
      ...(typeof choices?.human_skill === 'string' && choices.human_skill ? { human_skill: choices.human_skill } : {}),
      ...(choices?.versatile_origin_feat ? { versatile_origin_feat: choices.versatile_origin_feat } : {}),
    });
      dispatch({
        type: 'set',
        patch: { character: res.character as Character, summary: res.summary, levelUpOpen: false },
      });
      toast.success('Character leveled up');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Level up failed';
      toast.error(msg);
      dispatch({ type: 'set', patch: { error: msg } });
    }
  };

  const deleteCharacter = async () => {
    const id = state.activeId || characterId;
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
      const msg = e instanceof Error ? e.message : 'Delete failed';
      toast.error(msg);
      dispatch({ type: 'set', patch: { error: msg } });
    } finally {
      setDeleting(false);
    }
  };

  const { character, summary } = state;
  const activeId = state.activeId || characterId || null;
  const gameId = character?.game_id || DEFAULT_GAME_ID;
  const supportedGame = GAMES.some((g) => g.id === gameId);

  return (
    <AnimatedPage className="space-y-6">
      <PageHeader
        title="Characters"
        subtitle={
          mode === 'view' && character
            ? character.name
            : `Create and manage ${gameLabel(DEFAULT_GAME_ID)} character sheets.`
        }
        actions={
          mode === 'list' ? (
            <button
              type="button"
              className="btn-primary shrink-0 inline-flex items-center gap-2"
              onClick={() => navigate('/characters/new')}
            >
              <UserPlus size={16} /> New character
            </button>
          ) : undefined
        }
      />

      {state.error && (
        <m.div
          variants={fadeUp}
          className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-2 text-sm text-danger"
        >
          {state.error}
          {mode === 'view' && (
            <button type="button" className="ml-3 underline" onClick={() => navigate('/characters')}>
              Back to list
            </button>
          )}
        </m.div>
      )}

      {mode === 'list' && (
        <m.div variants={staggerContainer} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {!state.rosterLoaded ? (
            <ListLoading className="sm:col-span-2 lg:col-span-3" />
          ) : state.roster.length === 0 ? (
            <div className="sm:col-span-2 lg:col-span-3">
              <EmptyState
                icon={<Users size={32} />}
                title="No characters yet"
                description="Build a PHB 2024 character with guided creation."
                action={
                  <button type="button" className="btn-primary" onClick={() => navigate('/characters/new')}>
                    Create your first character
                  </button>
                }
              />
            </div>
          ) : (
            state.roster.map((r) => (
              <ListCard key={r.id} title={r.name} onClick={() => navigate(`/characters/${r.id}`)} />
            ))
          )}
        </m.div>
      )}

      {mode === 'wizard' && isNew && !newGameId && (
        <m.div variants={fadeUp} className="panel-glow p-6 space-y-4 max-w-lg">
          <h2 className="display-title text-lg">Choose game</h2>
          <p className="text-sm text-muted">Pick which ruleset this character uses.</p>
          <div className="grid gap-2">
            {GAMES.map((g) => {
              const config = getGameCharacterConfig(g.id);
              return (
                <button
                  key={g.id}
                  type="button"
                  className="play-chip text-left px-4 py-3 w-full"
                  disabled={config.creationFlow === 'immediate' && creatingImmediate}
                  onClick={() => {
                    if (config.creationFlow === 'immediate') {
                      void startImmediateCharacter(g.id);
                      return;
                    }
                    setNewGameId(g.id);
                  }}
                >
                  {g.label}
                </button>
              );
            })}
          </div>
          <button type="button" className="btn-ghost text-sm" onClick={() => navigate('/characters')}>
            Cancel
          </button>
        </m.div>
      )}

      {mode === 'wizard' && getGameCharacterConfig(newGameId ?? gameId).creationFlow === 'wizard' && (
        <m.div variants={fadeUp}>
          <GameCharacterWizard
            gameId={newGameId ?? gameId}
            initial={character || undefined}
            onSave={saveChar}
            onCancel={() => navigate(activeId ? `/characters/${activeId}` : '/characters')}
          />
        </m.div>
      )}

      {mode === 'wizard' && getGameCharacterConfig(gameId).creationFlow === 'immediate' && character && (
        <m.div variants={fadeUp}>
          <GameCharacterSetup
            gameId={gameId}
            characterId={activeId}
            entity={character as Record<string, unknown>}
            onChange={(entity) => dispatch({ type: 'set', patch: { character: entity as Character } })}
            onSaved={async (entity) => {
              await saveChar(entity as Character, { silentToast: true, alreadyPersisted: true });
            }}
          />
          <button
            type="button"
            className="btn-ghost mt-3 text-sm"
            onClick={() => navigate(activeId ? `/characters/${activeId}` : '/characters')}
          >
            {activeId ? 'Done' : 'Cancel'}
          </button>
        </m.div>
      )}

      {mode === 'view' && character && !supportedGame && (
        <EmptyState
          icon={<Users size={32} />}
          title="Game not supported yet"
          description={`This character uses "${gameLabel(gameId)}", which is not available in the UI yet.`}
          action={
            <button type="button" className="btn-ghost" onClick={() => navigate('/characters')}>
              Back to list
            </button>
          }
        />
      )}

      {mode === 'view' && character && supportedGame && (
        <CharacterDetailPanel
          character={character}
          activeId={activeId}
          summary={summary}
          charOptions={charOptions}
          onBack={() => navigate('/characters')}
          onEdit={() => navigate(`/characters/${activeId}/edit`)}
          onLevelUp={() => dispatch({ type: 'set', patch: { levelUpOpen: true } })}
          onSave={saveChar}
          onDelete={() => setConfirmDelete(true)}
          onChange={(c) => dispatch({ type: 'set', patch: { character: c } })}
        />
      )}

      {state.levelUpOpen && character && activeId && getGameCharacterConfig(gameId).supportsLevelUp && (
        <LevelUpDialog
          characterId={activeId}
          character={character}
          summary={summary}
          onConfirm={levelUp}
          onCancel={() => dispatch({ type: 'set', patch: { levelUpOpen: false } })}
        />
      )}

      <ConfirmDialog
        open={confirmDelete}
        title="Delete character"
        message={
          character
            ? `Delete "${character.name}"? This also deletes linked adventures and play sessions, and removes the character from campaigns.`
            : ''
        }
        onConfirm={deleteCharacter}
        onCancel={() => setConfirmDelete(false)}
        busy={deleting}
      />
    </AnimatedPage>
  );
}
