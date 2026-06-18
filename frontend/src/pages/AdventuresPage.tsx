import { useCallback, useEffect, useReducer, useState } from 'react';
import { m, AnimatePresence } from '../lib/framer';
import { Compass } from 'lucide-react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import ListCard from '../components/ui/ListCard';
import EmptyState from '../components/ui/EmptyState';
import ListLoading from '../components/ui/ListLoading';
import AnimatedPage from '../components/ui/AnimatedPage';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { fadeUp } from '../components/ui/motion';
import AdventureCreateForm from './adventures/AdventureCreateForm';
import AdventureDetailPanel from './adventures/AdventureDetailPanel';
import { adventuresReducer, initialAdventuresState } from './adventures/adventuresState';

export default function AdventuresPage() {
  const [state, dispatch] = useReducer(adventuresReducer, initialAdventuresState);
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    const [a, c, camps] = await Promise.all([api.listAdventures(), api.listCharacters(), api.listCampaigns()]);
    dispatch({
      type: 'set',
      patch: {
        adventures: a.adventures,
        characters: c.characters,
        campaigns: camps.campaigns,
        adventuresLoaded: true,
      },
    });
  }, []);

  useEffect(() => {
    load().catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [load]);

  const create = async () => {
    dispatch({ type: 'set', patch: { error: null } });
    try {
      const res = await api.createAdventure(state.form);
      dispatch({ type: 'set', patch: { selected: res.adventure, creating: false } });
      await load();
    } catch (e) {
      dispatch({ type: 'set', patch: { error: String(e) } });
    }
  };

  const open = async (id: string) => {
    const { adventure } = await api.getAdventure(id);
    dispatch({ type: 'set', patch: { selected: adventure } });
  };

  const deleteSelected = async () => {
    if (!confirmDelete) return;
    setDeleting(true);
    dispatch({ type: 'set', patch: { error: null } });
    try {
      await api.deleteAdventure(confirmDelete.id);
      if (state.selected?.id === confirmDelete.id) {
        dispatch({ type: 'set', patch: { selected: null } });
      }
      setConfirmDelete(null);
      await load();
    } catch (e) {
      dispatch({ type: 'set', patch: { error: String(e) } });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AnimatedPage className="space-y-6">
      <PageHeader
        title="Adventures"
        subtitle="Generate and browse adventure outlines: freeform hooks or Faerûn module content."
        actions={
          <button
            type="button"
            className="btn-primary"
            onClick={() => dispatch({ type: 'set', patch: { creating: true } })}
          >
            New adventure
          </button>
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

      <AnimatePresence>
        {state.creating && (
          <AdventureCreateForm
            form={state.form}
            characters={state.characters}
            campaigns={state.campaigns}
            onPatchForm={(patch) => dispatch({ type: 'patchForm', patch })}
            onCreate={create}
            onCancel={() => dispatch({ type: 'set', patch: { creating: false } })}
          />
        )}
      </AnimatePresence>

      <m.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="space-y-2">
          {!state.adventuresLoaded ? (
            <ListLoading />
          ) : state.adventures.length === 0 ? (
            <EmptyState
              icon={<Compass size={32} />}
              title="No adventures yet"
              description="Generate an adventure outline from a theme or Faerûn module."
              action={
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => dispatch({ type: 'set', patch: { creating: true } })}
                >
                  New adventure
                </button>
              }
            />
          ) : (
            state.adventures.map((a) => {
              const camp = state.campaigns.find((c) => c.id === (a as { campaign_id?: string }).campaign_id);
              const subtitle = camp ? `${a.mode} · ${camp.name}` : a.mode;
              return (
                <ListCard
                  key={a.id}
                  title={a.name}
                  subtitle={subtitle}
                  selected={state.selected?.id === a.id}
                  onClick={() => open(a.id)}
                />
              );
            })
          )}
        </div>

        {state.selected && (
          <AdventureDetailPanel
            adventure={state.selected}
            campaignName={state.campaigns.find((c) => c.id === state.selected?.campaign_id)?.name}
            onDelete={() => setConfirmDelete({ id: state.selected!.id, name: state.selected!.name })}
          />
        )}
      </m.div>

      <ConfirmDialog
        open={confirmDelete !== null}
        title="Delete adventure"
        message={
          confirmDelete ? `Delete "${confirmDelete.name}"? This also deletes any play sessions for this adventure.` : ''
        }
        onConfirm={deleteSelected}
        onCancel={() => setConfirmDelete(null)}
        busy={deleting}
      />
    </AnimatedPage>
  );
}
