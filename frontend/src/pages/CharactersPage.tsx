import { useEffect, useReducer, useState, type ComponentProps, type Dispatch } from 'react';
import { useMatch, useNavigate, useParams, type NavigateFunction } from 'react-router-dom';
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
import {
  charactersReducer,
  initialCharactersState,
  type CharactersAction,
  type CharactersState,
} from './characters/charactersState';
import { useCharactersPageActions, type SaveCharOptions } from './characters/useCharactersPageActions';

function useCharactersPageData({
  mode,
  characterId,
  isNew,
  gameId,
  load,
  loadCharacter,
  dispatch,
  setCharOptions,
}: {
  mode: 'list' | 'wizard' | 'view';
  characterId: string | undefined;
  isNew: boolean;
  gameId: string | undefined;
  load: () => Promise<void>;
  loadCharacter: (id: string) => Promise<void>;
  dispatch: Dispatch<CharactersAction>;
  setCharOptions: Dispatch<Record<string, unknown>>;
}) {
  useEffect(() => {
    load().catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [load, dispatch]);

  useEffect(() => {
    if (mode !== 'view' && mode !== 'wizard') {
      dispatch({ type: 'set', patch: { character: null, activeId: null, summary: {} } });
      return;
    }
    if (!characterId || isNew) return;
    loadCharacter(characterId).catch(() => {
      dispatch({ type: 'set', patch: { error: 'Character not found.', character: null, activeId: null } });
    });
  }, [characterId, isNew, mode, loadCharacter, dispatch]);

  useEffect(() => {
    if (mode !== 'view' && mode !== 'wizard') return;
    if (!characterId || isNew) return;
    api
      .getCharacterOptions(false, gameId || DEFAULT_GAME_ID)
      .then(setCharOptions)
      .catch(() => setCharOptions({}));
  }, [mode, characterId, isNew, gameId, setCharOptions]);
}

function CharactersWorkspace({
  mode,
  isNew,
  state,
  character,
  summary,
  activeId,
  gameId,
  supportedGame,
  charOptions,
  newGameId,
  creatingImmediate,
  saveChar,
  startImmediateCharacter,
  onPickGame,
  onConfirmDelete,
  dispatch,
  navigate,
}: {
  mode: 'list' | 'wizard' | 'view';
  isNew: boolean;
  state: CharactersState;
  character: Character | null;
  summary: Record<string, unknown>;
  activeId: string | null;
  gameId: string;
  supportedGame: boolean;
  charOptions: Record<string, unknown>;
  newGameId: string | null;
  creatingImmediate: boolean;
  saveChar: (c: Character, opts?: SaveCharOptions) => Promise<void>;
  startImmediateCharacter: (id: string) => Promise<void>;
  onPickGame: (id: string) => void;
  onConfirmDelete: () => void;
  dispatch: Dispatch<CharactersAction>;
  navigate: NavigateFunction;
}) {
  return (
    <>
      <CharactersErrorBanner error={state.error} showBack={mode === 'view'} onBack={() => navigate('/characters')} />
      {mode === 'list' && (
        <CharactersRoster
          roster={state.roster}
          loaded={state.rosterLoaded}
          onOpen={(id) => navigate(`/characters/${id}`)}
          onCreate={() => navigate('/characters/new')}
        />
      )}
      {mode === 'wizard' && (
        <CharactersWizardViews
          isNew={isNew}
          newGameId={newGameId}
          gameId={gameId}
          character={character}
          activeId={activeId}
          creatingImmediate={creatingImmediate}
          onPickGame={onPickGame}
          onImmediate={startImmediateCharacter}
          onSave={saveChar}
          onChange={(c) => dispatch({ type: 'set', patch: { character: c } })}
          onCancel={() => navigate(activeId ? `/characters/${activeId}` : '/characters')}
        />
      )}
      {mode === 'view' && character && (
        <CharactersView
          character={character}
          supportedGame={supportedGame}
          gameId={gameId}
          activeId={activeId}
          summary={summary}
          charOptions={charOptions}
          onSave={saveChar}
          onBack={() => navigate('/characters')}
          onEdit={() => navigate(`/characters/${activeId}/edit`)}
          onLevelUp={() => dispatch({ type: 'set', patch: { levelUpOpen: true } })}
          onDelete={onConfirmDelete}
          onChange={(c) => dispatch({ type: 'set', patch: { character: c } })}
        />
      )}
    </>
  );
}

function charactersPageMode(isNew: boolean, isEdit: boolean, characterId: string | undefined) {
  if (isNew || isEdit) return 'wizard' as const;
  if (characterId) return 'view' as const;
  return 'list' as const;
}

export default function CharactersPage() {
  const navigate = useNavigate();
  const { characterId } = useParams();
  const isNew = Boolean(useMatch('/characters/new'));
  const isEdit = Boolean(useMatch('/characters/:characterId/edit'));
  const mode = charactersPageMode(isNew, isEdit, characterId);

  const [state, dispatch] = useReducer(charactersReducer, initialCharactersState);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [charOptions, setCharOptions] = useState<Record<string, unknown>>({});
  const [newGameId, setNewGameId] = useState<string | null>(null);
  const [creatingImmediate, setCreatingImmediate] = useState(false);

  const { load, loadCharacter, saveChar, startImmediateCharacter, levelUp, deleteCharacter } = useCharactersPageActions(
    state,
    dispatch,
    characterId,
    newGameId,
    navigate,
    setDeleting,
    setConfirmDelete,
    setCreatingImmediate,
  );

  useCharactersPageData({
    mode,
    characterId,
    isNew,
    gameId: state.character?.game_id,
    load,
    loadCharacter,
    dispatch,
    setCharOptions,
  });

  const { character, summary } = state;
  const activeId = state.activeId || characterId || null;
  const gameId = character?.game_id || DEFAULT_GAME_ID;
  const supportedGame = GAMES.some((g) => g.id === gameId);

  return (
    <AnimatedPage className="space-y-6">
      <CharactersHeader mode={mode} character={character} onCreate={() => navigate('/characters/new')} />
      <CharactersWorkspace
        mode={mode}
        isNew={isNew}
        state={state}
        character={character}
        summary={summary}
        activeId={activeId}
        gameId={gameId}
        supportedGame={supportedGame}
        charOptions={charOptions}
        newGameId={newGameId}
        creatingImmediate={creatingImmediate}
        saveChar={saveChar}
        startImmediateCharacter={startImmediateCharacter}
        onPickGame={setNewGameId}
        onConfirmDelete={() => setConfirmDelete(true)}
        dispatch={dispatch}
        navigate={navigate}
      />
      <CharactersLevelUp
        open={state.levelUpOpen}
        character={character}
        activeId={activeId}
        gameId={gameId}
        summary={summary}
        onConfirm={levelUp}
        onCancel={() => dispatch({ type: 'set', patch: { levelUpOpen: false } })}
      />

      <ConfirmDialog
        open={confirmDelete}
        title="Delete character"
        message={
          character
            ? `Delete "${character.name}"? This also deletes linked adventures and play sessions, and removes the character from campaigns.`
            : ''
        }
        onConfirm={() => deleteCharacter(character)}
        onCancel={() => setConfirmDelete(false)}
        busy={deleting}
      />
    </AnimatedPage>
  );
}

function CharactersHeader({
  mode,
  character,
  onCreate,
}: {
  mode: 'wizard' | 'view' | 'list';
  character: Character | null;
  onCreate: () => void;
}) {
  return (
    <PageHeader
      title="Characters"
      subtitle={
        mode === 'view' && character
          ? character.name
          : `Create and manage ${gameLabel(DEFAULT_GAME_ID)} character sheets.`
      }
      actions={
        mode === 'list' ? (
          <button type="button" className="btn-primary shrink-0 inline-flex items-center gap-2" onClick={onCreate}>
            <UserPlus size={16} /> New character
          </button>
        ) : undefined
      }
    />
  );
}

function CharactersLevelUp({
  open,
  character,
  activeId,
  gameId,
  summary,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  character: Character | null;
  activeId: string | null;
  gameId: string;
  summary: Record<string, unknown>;
  onConfirm: ComponentProps<typeof LevelUpDialog>['onConfirm'];
  onCancel: () => void;
}) {
  if (!open || !character || !activeId || !getGameCharacterConfig(gameId).supportsLevelUp) return null;
  return (
    <LevelUpDialog
      characterId={activeId}
      character={character}
      summary={summary}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
}

function CharactersErrorBanner({
  error,
  showBack,
  onBack,
}: {
  error: string | null;
  showBack: boolean;
  onBack: () => void;
}) {
  if (!error) return null;
  return (
    <m.div variants={fadeUp} className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-2 text-sm text-danger">
      {error}
      {showBack && (
        <button type="button" className="ml-3 underline" onClick={onBack}>
          Back to list
        </button>
      )}
    </m.div>
  );
}

function CharactersRoster({
  roster,
  loaded,
  onOpen,
  onCreate,
}: {
  roster: { id: string; name: string }[];
  loaded: boolean;
  onOpen: (id: string) => void;
  onCreate: () => void;
}) {
  return (
    <m.div variants={staggerContainer} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {!loaded ? (
        <ListLoading className="sm:col-span-2 lg:col-span-3" />
      ) : roster.length === 0 ? (
        <div className="sm:col-span-2 lg:col-span-3">
          <EmptyState
            icon={<Users size={32} />}
            title="No characters yet"
            description="Build a PHB 2024 character with guided creation."
            action={
              <button type="button" className="btn-primary" onClick={onCreate}>
                Create your first character
              </button>
            }
          />
        </div>
      ) : (
        roster.map((r) => <ListCard key={r.id} title={r.name} onClick={() => onOpen(r.id)} />)
      )}
    </m.div>
  );
}

function CharactersWizardViews({
  isNew,
  newGameId,
  gameId,
  character,
  activeId,
  creatingImmediate,
  onPickGame,
  onImmediate,
  onSave,
  onChange,
  onCancel,
}: {
  isNew: boolean;
  newGameId: string | null;
  gameId: string;
  character: Character | null;
  activeId: string | null;
  creatingImmediate: boolean;
  onPickGame: (id: string) => void;
  onImmediate: (id: string) => void;
  onSave: (c: Character, opts?: SaveCharOptions) => Promise<void>;
  onChange: (c: Character) => void;
  onCancel: () => void;
}) {
  const wizardGameId = newGameId ?? gameId;
  const showPicker = isNew && !newGameId;
  const showWizard = getGameCharacterConfig(wizardGameId).creationFlow === 'wizard';
  const showImmediate = getGameCharacterConfig(gameId).creationFlow === 'immediate' && Boolean(character);
  return (
    <>
      {showPicker && (
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
                      void onImmediate(g.id);
                      return;
                    }
                    onPickGame(g.id);
                  }}
                >
                  {g.label}
                </button>
              );
            })}
          </div>
          <button type="button" className="btn-ghost text-sm" onClick={onCancel}>
            Cancel
          </button>
        </m.div>
      )}
      {showWizard && (
        <m.div variants={fadeUp}>
          <GameCharacterWizard
            gameId={wizardGameId}
            initial={character || undefined}
            onSave={onSave}
            onCancel={onCancel}
          />
        </m.div>
      )}
      {showImmediate && character && (
        <m.div variants={fadeUp}>
          <GameCharacterSetup
            gameId={gameId}
            characterId={activeId}
            entity={character as Record<string, unknown>}
            onChange={(entity) => onChange(entity as Character)}
            onSaved={async (entity) => {
              await onSave(entity as Character, { silentToast: true, alreadyPersisted: true });
            }}
          />
          <button type="button" className="btn-ghost mt-3 text-sm" onClick={onCancel}>
            {activeId ? 'Done' : 'Cancel'}
          </button>
        </m.div>
      )}
    </>
  );
}

function CharactersView({
  character,
  supportedGame,
  gameId,
  activeId,
  summary,
  charOptions,
  onSave,
  onBack,
  onEdit,
  onLevelUp,
  onDelete,
  onChange,
}: {
  character: Character;
  supportedGame: boolean;
  gameId: string;
  activeId: string | null;
  summary: Record<string, unknown>;
  charOptions: Record<string, unknown>;
  onSave: (c: Character, opts?: SaveCharOptions) => void | Promise<void>;
  onBack: () => void;
  onEdit: () => void;
  onLevelUp: () => void;
  onDelete: () => void;
  onChange: (c: Character) => void;
}) {
  if (!supportedGame) {
    return (
      <EmptyState
        icon={<Users size={32} />}
        title="Game not supported yet"
        description={`This character uses "${gameLabel(gameId)}", which is not available in the UI yet.`}
        action={
          <button type="button" className="btn-ghost" onClick={onBack}>
            Back to list
          </button>
        }
      />
    );
  }
  return (
    <CharacterDetailPanel
      character={character}
      activeId={activeId}
      summary={summary}
      charOptions={charOptions}
      onBack={onBack}
      onEdit={onEdit}
      onLevelUp={onLevelUp}
      onSave={onSave}
      onDelete={onDelete}
      onChange={onChange}
    />
  );
}
