import { useCallback, useEffect, useReducer, useState } from 'react';
import { useMatch, useNavigate, useParams } from 'react-router-dom';
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
  const navigate = useNavigate();
  const { adventureId } = useParams();
  const isNew = Boolean(useMatch('/adventures/new'));

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

  const open = useCallback(async (id: string) => {
    const { adventure } = await api.getAdventure(id);
    dispatch({ type: 'set', patch: { selected: adventure, error: null } });
  }, []);

  useEffect(() => {
    load().catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [load]);

  useEffect(() => {
    if (isNew) {
      dispatch({ type: 'set', patch: { selected: null, creating: true } });
      return;
    }
    if (!adventureId) {
      dispatch({ type: 'set', patch: { selected: null, creating: false } });
      return;
    }
    dispatch({ type: 'set', patch: { creating: false } });
    open(adventureId).catch(() => {
      dispatch({ type: 'set', patch: { error: 'Adventure not found.', selected: null } });
    });
  }, [adventureId, isNew, open]);

  const create = async () => {
    dispatch({ type: 'set', patch: { error: null } });
    try {
      const res = await api.createAdventure(state.form);
      dispatch({ type: 'set', patch: { creating: false } });
      await load();
      navigate(`/adventures/${res.id}`);
    } catch (e) {
      dispatch({ type: 'set', patch: { error: String(e) } });
    }
  };

  const deleteSelected = async () => {
    if (!confirmDelete) return;
    setDeleting(true);
    dispatch({ type: 'set', patch: { error: null } });
    try {
      await api.deleteAdventure(confirmDelete.id);
      setConfirmDelete(null);
      await load();
      navigate('/adventures');
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
          !isNew && !adventureId ? (
            <button type="button" className="btn-primary" onClick={() => navigate('/adventures/new')}>
              New adventure
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
          {adventureId && (
            <button type="button" className="ml-3 underline" onClick={() => navigate('/adventures')}>
              Back to list
            </button>
          )}
        </m.div>
      )}

      <AnimatePresence>
        {(isNew || state.creating) && (
          <AdventureCreateForm
            form={state.form}
            characters={state.characters}
            campaigns={state.campaigns}
            onPatchForm={(patch) => dispatch({ type: 'patchForm', patch })}
            onCreate={create}
            onCancel={() => navigate('/adventures')}
          />
        )}
      </AnimatePresence>

      {!isNew && (
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
                  <button type="button" className="btn-primary" onClick={() => navigate('/adventures/new')}>
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
                    onClick={() => navigate(`/adventures/${a.id}`)}
                  />
                );
              })
            )}
          </div>

          {state.selected && adventureId && (
            <AdventureDetailPanel
              adventure={state.selected}
              campaignName={state.campaigns.find((c) => c.id === state.selected?.campaign_id)?.name}
              onDelete={() => setConfirmDelete({ id: state.selected!.id, name: state.selected!.name })}
            />
          )}
        </m.div>
      )}

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
