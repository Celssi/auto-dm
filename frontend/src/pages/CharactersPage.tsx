import { useCallback, useEffect, useReducer, useState } from 'react';
import { m } from '../lib/framer';
import { UserPlus, Users } from 'lucide-react';
import { api } from '../api/client';
import type { Character } from '../types';
import CharacterWizard from '../components/character-sheet/CharacterWizard';
import LevelUpDialog from '../components/character-sheet/LevelUpDialog';
import PageHeader from '../components/ui/PageHeader';
import ListCard from '../components/ui/ListCard';
import EmptyState from '../components/ui/EmptyState';
import ListLoading from '../components/ui/ListLoading';
import AnimatedPage from '../components/ui/AnimatedPage';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { fadeUp, staggerContainer } from '../components/ui/motion';
import CharacterDetailPanel from './characters/CharacterDetailPanel';
import { charactersReducer, initialCharactersState } from './characters/charactersState';

export default function CharactersPage() {
  const [state, dispatch] = useReducer(charactersReducer, initialCharactersState);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [charOptions, setCharOptions] = useState<Record<string, unknown>>({});

  const load = useCallback(async () => {
    const { characters } = await api.listCharacters();
    dispatch({ type: 'set', patch: { roster: characters, rosterLoaded: true } });
  }, []);

  const openChar = useCallback(async (id: string) => {
    const [{ character: c }, sum] = await Promise.all([api.getCharacter(id), api.getCharacterSummary(id)]);
    dispatch({
      type: 'set',
      patch: { character: c as Character, summary: sum.summary, activeId: id, mode: 'view' },
    });
  }, []);

  useEffect(() => {
    load().catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [load]);

  useEffect(() => {
    if (state.mode === 'view' && state.activeId) {
      api
        .getCharacterOptions(false)
        .then(setCharOptions)
        .catch(() => setCharOptions({}));
    }
  }, [state.mode, state.activeId]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (id) openChar(id).catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [openChar]);

  const saveChar = async (c: Character) => {
    let id = state.activeId;
    if (id) {
      await api.updateCharacter(id, c as Record<string, unknown>);
    } else {
      const res = await api.createCharacter(c as Record<string, unknown>);
      id = res.id;
      dispatch({ type: 'set', patch: { activeId: res.id, character: res.character as Character } });
    }
    await load();
    dispatch({ type: 'set', patch: { mode: 'view' } });
    if (id) {
      const sum = await api.getCharacterSummary(id);
      dispatch({ type: 'set', patch: { summary: sum.summary, character: sum.character as Character } });
    }
  };

  const levelUp = async (
    hpRoll: number | undefined,
    asiChoices: Record<string, unknown>[],
    className?: string,
    spells?: { cantrips?: string[]; prepared_spells?: string[]; known_spells?: string[] },
    choices?: Partial<Character>,
  ) => {
    if (!state.activeId) return;
    const res = await api.levelUpCharacter(state.activeId, {
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
  };

  const deleteCharacter = async () => {
    if (!state.activeId || !character) return;
    setDeleting(true);
    dispatch({ type: 'set', patch: { error: null } });
    try {
      await api.deleteCharacter(state.activeId);
      setConfirmDelete(false);
      dispatch({ type: 'set', patch: { activeId: null, character: null, mode: 'list' } });
      await load();
    } catch (e) {
      dispatch({ type: 'set', patch: { error: String(e) } });
    } finally {
      setDeleting(false);
    }
  };

  const { character, summary, mode } = state;

  return (
    <AnimatedPage className="space-y-6">
      <PageHeader
        title="Characters"
        subtitle={mode === 'view' && character ? character.name : 'Create and manage D&D 5e character sheets.'}
        actions={
          mode !== 'wizard' ? (
            <button
              type="button"
              className="btn-primary shrink-0 inline-flex items-center gap-2"
              onClick={() => dispatch({ type: 'set', patch: { activeId: null, character: null, mode: 'wizard' } })}
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
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() =>
                      dispatch({ type: 'set', patch: { activeId: null, character: null, mode: 'wizard' } })
                    }
                  >
                    Create your first character
                  </button>
                }
              />
            </div>
          ) : (
            state.roster.map((r) => <ListCard key={r.id} title={r.name} onClick={() => openChar(r.id)} />)
          )}
        </m.div>
      )}

      {mode === 'wizard' && (
        <m.div variants={fadeUp}>
          <CharacterWizard
            initial={character || undefined}
            onSave={saveChar}
            onCancel={() => dispatch({ type: 'set', patch: { mode: 'list' } })}
          />
        </m.div>
      )}

      {mode === 'view' && character && (
        <CharacterDetailPanel
          character={character}
          activeId={state.activeId}
          summary={summary}
          charOptions={charOptions}
          onBack={() => dispatch({ type: 'set', patch: { mode: 'list' } })}
          onEdit={() => dispatch({ type: 'set', patch: { mode: 'wizard' } })}
          onLevelUp={() => dispatch({ type: 'set', patch: { levelUpOpen: true } })}
          onSave={saveChar}
          onDelete={() => setConfirmDelete(true)}
          onChange={(c) => dispatch({ type: 'set', patch: { character: c } })}
        />
      )}

      {state.levelUpOpen && character && state.activeId && (
        <LevelUpDialog
          characterId={state.activeId}
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
