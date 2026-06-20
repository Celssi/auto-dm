import { useEffect, useReducer, useState } from 'react';
import { m, AnimatePresence } from '../lib/framer';
import PageHeader from '../components/ui/PageHeader';
import AnimatedPage from '../components/ui/AnimatedPage';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { fadeUp } from '../components/ui/motion';
import CampaignCreateForm from './campaigns/CampaignCreateForm';
import CampaignDetailPanel from './campaigns/CampaignDetailPanel';
import CampaignListPanel from './campaigns/CampaignListPanel';
import { campaignsReducer, initialCampaignsState } from './campaigns/campaignsState';
import { useCampaignsPageActions } from './campaigns/useCampaignsPageActions';

export default function CampaignsPage() {
  const [state, dispatch] = useReducer(campaignsReducer, initialCampaignsState);
  const [confirm, setConfirm] = useState<
    { kind: 'campaign'; id: string; name: string } | { kind: 'adventure'; id: string; name: string } | null
  >(null);
  const [deleting, setDeleting] = useState(false);

  const {
    load,
    open,
    create,
    openCreateForm,
    generateCampaign,
    startNewAdventure,
    playAdventure,
    openEntry,
    saveEntry,
    onTabChange,
    linkCharacter,
    copyCampaign,
    confirmDelete,
  } = useCampaignsPageActions(state, dispatch, confirm, setConfirm, setDeleting);

  useEffect(() => {
    load().catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [load]);

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
          <CampaignListPanel state={state} onOpen={open} onOpenCreateForm={openCreateForm} />
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
            onToggleCopy={() =>
              dispatch({
                type: 'set',
                patch: {
                  copyOpen: !state.copyOpen,
                  copyForm: state.copyOpen
                    ? state.copyForm
                    : {
                        character_id: state.characters[0]?.id ?? '',
                        name: '',
                      },
                },
              })
            }
            onPatchCopyForm={(patch) => dispatch({ type: 'patchCopyForm', patch })}
            onPatchAdventureForm={(patch) => dispatch({ type: 'patchAdventureForm', patch })}
            onStartNewAdventure={startNewAdventure}
            onPlayAdventure={playAdventure}
            onLinkCharacter={linkCharacter}
            onCopyCampaign={copyCampaign}
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
