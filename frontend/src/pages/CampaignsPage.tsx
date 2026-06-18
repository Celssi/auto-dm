import { useCallback, useEffect, useReducer, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { m, AnimatePresence } from '../lib/framer';
import { BookOpen } from 'lucide-react';
import { api } from '../api/client';
import PageHeader from '../components/ui/PageHeader';
import ListCard from '../components/ui/ListCard';
import EmptyState from '../components/ui/EmptyState';
import ListLoading from '../components/ui/ListLoading';
import AnimatedPage from '../components/ui/AnimatedPage';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { fadeUp } from '../components/ui/motion';
import CampaignCreateForm from './campaigns/CampaignCreateForm';
import CampaignDetailPanel from './campaigns/CampaignDetailPanel';
import { campaignsReducer, initialCampaignsState, type CampaignTab } from './campaigns/campaignsState';

export default function CampaignsPage() {
  const navigate = useNavigate();
  const [state, dispatch] = useReducer(campaignsReducer, initialCampaignsState);
  const [confirm, setConfirm] = useState<
    { kind: 'campaign'; id: string; name: string } | { kind: 'adventure'; id: string; name: string } | null
  >(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    const [res, chars] = await Promise.all([api.listCampaigns(), api.listCharacters()]);
    dispatch({ type: 'set', patch: { campaigns: res.campaigns, characters: chars.characters, campaignsLoaded: true } });
  }, []);

  const loadAdventures = useCallback(async (campaignId: string) => {
    dispatch({ type: 'set', patch: { adventuresLoaded: false } });
    const res = await api.listCampaignAdventures(campaignId);
    dispatch({ type: 'set', patch: { campaignAdventures: res.adventures, adventuresLoaded: true } });
  }, []);

  useEffect(() => {
    load().catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [load]);

  const open = async (id: string) => {
    dispatch({ type: 'set', patch: { entry: null, newAdventureOpen: false } });
    const { campaign } = await api.getCampaign(id);
    const defaultChar = campaign.character_ids?.[0] || '';
    dispatch({
      type: 'set',
      patch: { selected: campaign, tab: 'story', adventureForm: { ...state.adventureForm, character_id: defaultChar } },
    });
    await loadAdventures(id);
  };

  const create = async () => {
    dispatch({ type: 'set', patch: { error: null } });
    try {
      const res = await api.createCampaign(state.form);
      dispatch({ type: 'set', patch: { selected: res.campaign, creating: false, form: { name: '', story_arc: '' } } });
      await load();
      await loadAdventures(res.id);
    } catch (e) {
      dispatch({ type: 'set', patch: { error: String(e) } });
    }
  };

  const openCreateForm = () => {
    const defaultChar = state.generateForm.character_id || state.characters[0]?.id || '';
    dispatch({
      type: 'set',
      patch: {
        creating: true,
        generateForm: { ...state.generateForm, character_id: defaultChar },
      },
    });
  };

  const generateCampaign = async () => {
    const { generateForm } = state;
    if (!generateForm.character_id || !generateForm.theme.trim()) return;
    dispatch({ type: 'set', patch: { error: null, generating: true } });
    try {
      const result = await api.generateCampaign({
        character_id: generateForm.character_id,
        mode: generateForm.mode,
        theme: generateForm.theme.trim(),
        adventure_count: generateForm.adventure_count,
        include_faerun: generateForm.include_faerun,
        campaign_name: generateForm.campaign_name.trim(),
        bootstrap_first: generateForm.bootstrap_first,
      });
      const { campaign } = await api.getCampaign(result.campaign_id);
      dispatch({
        type: 'set',
        patch: {
          selected: campaign,
          creating: false,
          tab: 'adventures',
          generateForm: { ...generateForm, theme: '', campaign_name: '' },
        },
      });
      await load();
      await loadAdventures(result.campaign_id);
      if (result.session_id) {
        navigate(`/play/${result.session_id}`);
      }
    } catch (e) {
      dispatch({
        type: 'set',
        patch: { error: e instanceof Error ? e.message : 'Failed to generate campaign' },
      });
    } finally {
      dispatch({ type: 'set', patch: { generating: false } });
    }
  };

  const startNewAdventure = async () => {
    const { selected, adventureForm } = state;
    if (!selected || !adventureForm.character_id) return;
    if (!adventureForm.auto_continue && !adventureForm.theme.trim()) return;
    dispatch({ type: 'set', patch: { error: null, bootstrapping: true } });
    try {
      const result = await api.bootstrapCampaignAdventure({
        campaign_id: selected.id,
        character_id: adventureForm.character_id,
        mode: adventureForm.mode,
        theme: adventureForm.theme.trim(),
        include_faerun: adventureForm.include_faerun,
        adventure_name: adventureForm.adventure_name.trim(),
        auto_continue: adventureForm.auto_continue,
      });
      dispatch({
        type: 'set',
        patch: {
          newAdventureOpen: false,
          adventureForm: { ...adventureForm, theme: '', adventure_name: '', auto_continue: false },
        },
      });
      await loadAdventures(selected.id);
      navigate(`/play/${result.session_id}`);
    } catch (e) {
      dispatch({
        type: 'set',
        patch: { error: e instanceof Error ? e.message : 'Failed to start adventure' },
      });
    } finally {
      dispatch({ type: 'set', patch: { bootstrapping: false } });
    }
  };

  const playAdventure = async (adventureId: string) => {
    if (!state.selected) return;
    dispatch({ type: 'set', patch: { error: null, bootstrapping: true } });
    try {
      const { session_id } = await api.startAdventureSession(adventureId);
      await loadAdventures(state.selected.id);
      navigate(`/play/${session_id}`);
    } catch (e) {
      dispatch({
        type: 'set',
        patch: { error: e instanceof Error ? e.message : 'Failed to start session' },
      });
    } finally {
      dispatch({ type: 'set', patch: { bootstrapping: false } });
    }
  };

  const openEntry = async (kind: 'npc' | 'location', id: string) => {
    if (!state.selected) return;
    if (kind === 'npc') {
      const { npc } = await api.getCampaignNpc(state.selected.id, id);
      dispatch({ type: 'set', patch: { entry: npc } });
    } else {
      const { location } = await api.getCampaignLocation(state.selected.id, id);
      dispatch({ type: 'set', patch: { entry: location } });
    }
  };

  const saveEntry = async () => {
    const { selected, entry, tab } = state;
    if (!selected || !entry) return;
    if (tab === 'npcs') {
      await api.updateCampaignNpc(selected.id, entry.id, { name: entry.name, body: entry.body });
    } else if (tab === 'locations') {
      await api.updateCampaignLocation(selected.id, entry.id, { name: entry.name, body: entry.body });
    }
    await open(selected.id);
    dispatch({ type: 'set', patch: { entry: null } });
  };

  const onTabChange = (tab: CampaignTab) => {
    dispatch({ type: 'set', patch: { tab, entry: null, newAdventureOpen: false } });
  };

  const confirmDelete = async () => {
    if (!confirm) return;
    setDeleting(true);
    dispatch({ type: 'set', patch: { error: null } });
    try {
      if (confirm.kind === 'campaign') {
        await api.deleteCampaign(confirm.id);
        dispatch({ type: 'set', patch: { selected: null } });
        await load();
      } else {
        await api.deleteAdventure(confirm.id);
        if (state.selected) {
          await loadAdventures(state.selected.id);
        }
        await load();
      }
      setConfirm(null);
    } catch (e) {
      dispatch({ type: 'set', patch: { error: String(e) } });
    } finally {
      setDeleting(false);
    }
  };

  const confirmMessage =
    confirm?.kind === 'campaign'
      ? `Delete "${confirm.name}"? This also deletes all adventures, play sessions, NPCs, and locations in this campaign. Characters are kept.`
      : confirm?.kind === 'adventure'
        ? `Delete "${confirm.name}"? This also deletes any play sessions for this adventure.`
        : '';

  return (
    <AnimatedPage className="space-y-6">
      <PageHeader
        title="Campaigns"
        subtitle="Story arcs, adventures, NPCs, and locations. Shared memory across every adventure in a campaign."
        actions={
          <button type="button" className="btn-primary" onClick={openCreateForm}>
            New campaign
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
          <CampaignCreateForm
            createMode={state.createMode}
            form={state.form}
            generateForm={state.generateForm}
            characters={state.characters}
            generating={state.generating}
            onCreateModeChange={(createMode) => dispatch({ type: 'set', patch: { createMode } })}
            onPatchForm={(patch) => dispatch({ type: 'patchForm', patch })}
            onPatchGenerateForm={(patch) => dispatch({ type: 'patchGenerateForm', patch })}
            onCreateManual={create}
            onGenerate={generateCampaign}
            onCancel={() => dispatch({ type: 'set', patch: { creating: false } })}
          />
        )}
      </AnimatePresence>

      <m.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="space-y-2">
          {!state.campaignsLoaded ? (
            <ListLoading />
          ) : state.campaigns.length === 0 ? (
            <EmptyState
              icon={<BookOpen size={32} />}
              title="No campaigns yet"
              description="Create a campaign to track your story arc, NPCs, and locations."
              action={
                <button type="button" className="btn-primary" onClick={openCreateForm}>
                  New campaign
                </button>
              }
            />
          ) : (
            state.campaigns.map((c) => (
              <ListCard
                key={c.id}
                title={c.name}
                subtitle={c.id}
                selected={state.selected?.id === c.id}
                onClick={() => open(c.id)}
              />
            ))
          )}
        </div>

        {state.selected && (
          <CampaignDetailPanel
            campaign={state.selected}
            state={state}
            onTabChange={onTabChange}
            onOpenEntry={openEntry}
            onSaveEntry={saveEntry}
            onSetEntry={(entry) => dispatch({ type: 'set', patch: { entry } })}
            onToggleNewAdventure={() => dispatch({ type: 'set', patch: { newAdventureOpen: !state.newAdventureOpen } })}
            onPatchAdventureForm={(patch) => dispatch({ type: 'patchAdventureForm', patch })}
            onStartNewAdventure={startNewAdventure}
            onPlayAdventure={playAdventure}
            onDelete={() => setConfirm({ kind: 'campaign', id: state.selected!.id, name: state.selected!.name })}
            onDeleteAdventure={(id) => {
              const adv = state.campaignAdventures.find((a) => a.id === id);
              setConfirm({ kind: 'adventure', id, name: adv?.name || id });
            }}
          />
        )}
      </m.div>

      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.kind === 'campaign' ? 'Delete campaign' : 'Delete adventure'}
        message={confirmMessage}
        onConfirm={confirmDelete}
        onCancel={() => setConfirm(null)}
        busy={deleting}
      />
    </AnimatedPage>
  );
}
