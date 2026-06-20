import { useCallback, useEffect, useReducer, useState } from 'react';
import { m } from '../lib/framer';
import { UserPlus, Users } from 'lucide-react';
import { api } from '../api/client';
import type { Character } from '../types';
import CharacterWizard from '../components/character-sheet/CharacterWizard';
import CharacterSheetView from '../components/character-sheet/CharacterSheetView';
import LevelUpDialog from '../components/character-sheet/LevelUpDialog';
import MulticlassPanel from '../components/character-sheet/MulticlassPanel';
import { displayLabel } from '../lib/displayText';
import GlossaryTip from '../components/ui/GlossaryTip';
import PageHeader from '../components/ui/PageHeader';
import ListCard from '../components/ui/ListCard';
import EmptyState from '../components/ui/EmptyState';
import ListLoading from '../components/ui/ListLoading';
import AnimatedPage from '../components/ui/AnimatedPage';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { fadeUp, staggerContainer } from '../components/ui/motion';
import { charactersReducer, initialCharactersState } from './characters/charactersState';

export default function CharactersPage() {
  const [state, dispatch] = useReducer(charactersReducer, initialCharactersState);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

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
  ) => {
    if (!state.activeId) return;
    const res = await api.levelUpCharacter(state.activeId, {
      hp_roll: hpRoll,
      asi_choices: asiChoices,
      class_name: className,
      ...spells,
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
  const unlockedFeatures = summary.unlocked_features as
    | { class_features?: Record<string, string[]>; subclass_features?: Record<string, string[]> }
    | undefined;

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
        <m.div variants={fadeUp} className="space-y-5">
          <div className="flex flex-wrap items-center gap-2 panel-glow p-3">
            <button
              type="button"
              className="btn-ghost"
              onClick={() => dispatch({ type: 'set', patch: { mode: 'list' } })}
            >
              ← Back
            </button>
            <div className="w-px h-6 bg-border hidden sm:block" />
            <button
              type="button"
              className="btn-ghost"
              onClick={() => dispatch({ type: 'set', patch: { mode: 'wizard' } })}
            >
              Edit
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => dispatch({ type: 'set', patch: { levelUpOpen: true } })}
            >
              Level up
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={async () => {
                const { downloadCharacterPdf } = await import('../components/character-sheet/CharacterSheetPdf');
                downloadCharacterPdf(character);
              }}
            >
              Export PDF
            </button>
            <button type="button" className="btn-primary ml-auto" onClick={() => saveChar(character)}>
              Save changes
            </button>
            <button type="button" className="btn-danger" onClick={() => setConfirmDelete(true)}>
              Delete
            </button>
          </div>

          {Boolean(summary.needs_asi) && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
              ASI or feat choice available. Level up or edit to apply.
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <MulticlassPanel
              character={{ ...character, id: state.activeId || undefined }}
              onChange={(classes) => dispatch({ type: 'set', patch: { character: { ...character, classes } } })}
            />
            {unlockedFeatures && (
              <div className="panel p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-accent mb-3">Unlocked features</h3>
                <div className="space-y-2 text-sm">
                  {Object.entries(unlockedFeatures.class_features || {}).map(([cid, feats]) => (
                    <div key={cid}>
                      <span className="text-muted">{displayLabel(cid)}</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {(feats as string[]).map((f) => (
                          <GlossaryTip key={f} name={f} />
                        ))}
                      </div>
                    </div>
                  ))}
                  {Object.entries(unlockedFeatures.subclass_features || {}).map(([key, feats]) => (
                    <div key={key}>
                      <span className="text-muted">{displayLabel(key)}</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {(feats as string[]).map((f) => (
                          <GlossaryTip key={f} name={f} />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <CharacterSheetView
            character={character}
            summary={summary}
            editable
            onChange={(c) => dispatch({ type: 'set', patch: { character: c as Character } })}
          />
        </m.div>
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
