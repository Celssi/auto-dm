import { useEffect, useReducer, useRef, useState, type Dispatch } from 'react';
import { useMatch, useNavigate, useParams, type NavigateFunction } from 'react-router-dom';
import { m, AnimatePresence } from '../lib/framer';
import PageHeader from '../components/ui/PageHeader';
import AnimatedPage from '../components/ui/AnimatedPage';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { fadeUp } from '../components/ui/motion';
import CampaignCreateForm from './campaigns/CampaignCreateForm';
import CampaignDetailPanel from './campaigns/CampaignDetailPanel';
import CampaignListPanel from './campaigns/CampaignListPanel';
import {
  campaignsReducer,
  initialCampaignsState,
  type CampaignTab,
  type CampaignsAction,
  type CampaignsState,
} from './campaigns/campaignsState';
import { useCampaignsPageActions } from './campaigns/useCampaignsPageActions';
import { useLoadedCharacterAdventure } from '../games/brambletrek/CampaignStartFields';

const CAMPAIGN_TABS = new Set<CampaignTab>(['story', 'adventures', 'npcs', 'locations']);

export default function CampaignsPage() {
  const navigate = useNavigate();
  const { campaignId, tab: tabParam } = useParams();
  const isNew = Boolean(useMatch('/campaigns/new'));
  const tab = tabParam && CAMPAIGN_TABS.has(tabParam as CampaignTab) ? (tabParam as CampaignTab) : 'story';

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
    bootstrapBrambletrekCampaign,
    startNewAdventure,
    playAdventure,
    openEntry,
    saveEntry,
    onTabChange,
    linkCharacter,
    copyCampaign,
    confirmDelete,
  } = useCampaignsPageActions(state, dispatch, confirm, setConfirm, setDeleting, navigate);

  useGenerateAdventureSync(state, dispatch, isNew);

  const openRef = useRef(open);
  const openCreateFormRef = useRef(openCreateForm);
  const openRequestRef = useRef(0);
  const loadedCampaignIdRef = useRef<string | null>(null);

  useEffect(() => {
    openRef.current = open;
    openCreateFormRef.current = openCreateForm;
  }, [open, openCreateForm]);

  useEffect(() => {
    load().catch((e) => dispatch({ type: 'set', patch: { error: String(e) } }));
  }, [load]);

  useEffect(() => {
    dispatch({ type: 'set', patch: { tab } });
  }, [tab]);

  useEffect(() => {
    if (isNew) {
      loadedCampaignIdRef.current = null;
      openCreateFormRef.current();
      return;
    }
    if (!campaignId) {
      loadedCampaignIdRef.current = null;
      dispatch({ type: 'set', patch: { selected: null, creating: false } });
      return;
    }

    dispatch({ type: 'set', patch: { creating: false } });

    if (loadedCampaignIdRef.current === campaignId) return;

    loadedCampaignIdRef.current = campaignId;
    const seq = ++openRequestRef.current;
    openRef.current(campaignId).catch(() => {
      if (seq !== openRequestRef.current) return;
      loadedCampaignIdRef.current = null;
      dispatch({ type: 'set', patch: { error: 'Campaign not found.', selected: null } });
    });
  }, [campaignId, isNew]);

  const handleTabChange = (nextTab: CampaignTab) => {
    if (!campaignId) return;
    onTabChange(nextTab);
    navigate(`/campaigns/${campaignId}/${nextTab}`);
  };

  const handleOpenCreateForm = () => {
    openCreateForm();
    navigate('/campaigns/new');
  };

  const handleCreate = async () => {
    const id = await create();
    if (id) navigate(`/campaigns/${id}`);
  };

  const handleBootstrapBrambletrek = async () => {
    const sessionId = await bootstrapBrambletrekCampaign();
    if (sessionId) navigate(`/play/${sessionId}`);
  };

  const handleGenerateCampaign = async () => {
    await generateCampaign();
  };

  const handleCopyCampaign = async () => {
    const id = await copyCampaign();
    if (id) navigate(`/campaigns/${id}/adventures`);
  };

  const handleConfirmDelete = async () => {
    const deletedCampaign = confirm?.kind === 'campaign';
    await confirmDelete();
    if (deletedCampaign) navigate('/campaigns');
  };

  const confirmMessage = deleteConfirmMessage(confirm);

  return (
    <AnimatedPage className="space-y-6">
      <PageHeader
        title="Campaigns"
        subtitle="Story arcs, adventures, NPCs, and locations. Shared memory across every adventure in a campaign."
        actions={
          !isNew && !campaignId ? (
            <button type="button" className="btn-primary" onClick={handleOpenCreateForm}>
              New campaign
            </button>
          ) : undefined
        }
      />

      <CampaignsErrorBanner error={state.error} campaignId={campaignId} onBack={() => navigate('/campaigns')} />

      <AnimatePresence>
        {(isNew || state.creating) && (
          <CampaignCreateForm
            createMode={state.createMode}
            form={state.form}
            generateForm={state.generateForm}
            characters={state.characters}
            generating={state.generating}
            onCreateModeChange={(createMode) => dispatch({ type: 'set', patch: { createMode } })}
            onPatchForm={(patch) => dispatch({ type: 'patchForm', patch })}
            onPatchGenerateForm={(patch) => dispatch({ type: 'patchGenerateForm', patch })}
            onCreateManual={handleCreate}
            onGenerate={handleGenerateCampaign}
            onBootstrapBrambletrek={handleBootstrapBrambletrek}
            onCancel={() => navigate('/campaigns')}
          />
        )}
      </AnimatePresence>

      {!isNew && (
        <CampaignBrowser
          state={state}
          campaignId={campaignId}
          navigate={navigate}
          dispatch={dispatch}
          openEntry={openEntry}
          saveEntry={saveEntry}
          handleTabChange={handleTabChange}
          startNewAdventure={startNewAdventure}
          playAdventure={playAdventure}
          linkCharacter={linkCharacter}
          handleCopyCampaign={handleCopyCampaign}
          handleOpenCreateForm={handleOpenCreateForm}
          setConfirm={setConfirm}
        />
      )}

      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.kind === 'campaign' ? 'Delete campaign' : 'Delete adventure'}
        message={confirmMessage}
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirm(null)}
        busy={deleting}
      />
    </AnimatedPage>
  );
}

function useGenerateAdventureSync(state: CampaignsState, dispatch: Dispatch<CampaignsAction>, isNew: boolean) {
  const generateCharacter = state.characters.find((c) => c.id === state.generateForm.character_id);
  const syncGenerateAdventure = (isNew || state.creating) && generateCharacter?.game_id === 'brambletrek';
  const loadedGenerateAdventure = useLoadedCharacterAdventure(state.generateForm.character_id, syncGenerateAdventure);
  const [syncedGenerateCharacterId, setSyncedGenerateCharacterId] = useState('');
  if (!syncGenerateAdventure || !state.generateForm.character_id) {
    if (syncedGenerateCharacterId) setSyncedGenerateCharacterId('');
    return;
  }
  if (loadedGenerateAdventure === undefined || syncedGenerateCharacterId === state.generateForm.character_id) return;
  setSyncedGenerateCharacterId(state.generateForm.character_id);
  dispatch({ type: 'patchGenerateForm', patch: { active_adventure: loadedGenerateAdventure } });
}

function CampaignsErrorBanner({
  error,
  campaignId,
  onBack,
}: {
  error: string | null;
  campaignId: string | undefined;
  onBack: () => void;
}) {
  if (!error) return null;
  return (
    <m.div variants={fadeUp} className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-2 text-sm text-danger">
      {error}
      {campaignId && (
        <button type="button" className="ml-3 underline" onClick={onBack}>
          Back to list
        </button>
      )}
    </m.div>
  );
}

function deleteConfirmMessage(
  confirm: { kind: 'campaign'; id: string; name: string } | { kind: 'adventure'; id: string; name: string } | null,
) {
  if (confirm?.kind === 'campaign') {
    return `Delete "${confirm.name}"? This also deletes all adventures, play sessions, NPCs, and locations in this campaign. Characters are kept.`;
  }
  if (confirm?.kind === 'adventure') {
    return `Delete "${confirm.name}"? This also deletes any play sessions for this adventure.`;
  }
  return '';
}

function CampaignBrowser({
  state,
  campaignId,
  navigate,
  dispatch,
  openEntry,
  saveEntry,
  handleTabChange,
  startNewAdventure,
  playAdventure,
  linkCharacter,
  handleCopyCampaign,
  handleOpenCreateForm,
  setConfirm,
}: {
  state: CampaignsState;
  campaignId: string | undefined;
  navigate: NavigateFunction;
  dispatch: Dispatch<CampaignsAction>;
  openEntry: (kind: 'npc' | 'location', id: string) => void;
  saveEntry: () => Promise<void>;
  handleTabChange: (tab: CampaignTab) => void;
  startNewAdventure: () => Promise<void>;
  playAdventure: (id: string) => void;
  linkCharacter: (characterId: string) => Promise<void>;
  handleCopyCampaign: () => Promise<void>;
  handleOpenCreateForm: () => void;
  setConfirm: (
    value: { kind: 'campaign'; id: string; name: string } | { kind: 'adventure'; id: string; name: string } | null,
  ) => void;
}) {
  return (
    <m.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div className="space-y-2">
        <CampaignListPanel
          state={state}
          onOpen={(id) => navigate(`/campaigns/${id}`)}
          onOpenCreateForm={handleOpenCreateForm}
        />
      </div>
      {state.selected && campaignId && (
        <CampaignDetailPanel
          campaign={state.selected}
          state={state}
          onTabChange={handleTabChange}
          onOpenEntry={openEntry}
          onSaveEntry={saveEntry}
          onSetEntry={(entry) => dispatch({ type: 'set', patch: { entry } })}
          onToggleNewAdventure={() => dispatch({ type: 'set', patch: { newAdventureOpen: !state.newAdventureOpen } })}
          onToggleCopy={() =>
            dispatch({
              type: 'set',
              patch: {
                copyOpen: !state.copyOpen,
                copyForm: state.copyOpen ? state.copyForm : { character_id: state.characters[0]?.id ?? '', name: '' },
              },
            })
          }
          onPatchCopyForm={(patch) => dispatch({ type: 'patchCopyForm', patch })}
          onPatchAdventureForm={(patch) => dispatch({ type: 'patchAdventureForm', patch })}
          onStartNewAdventure={startNewAdventure}
          onPlayAdventure={playAdventure}
          onLinkCharacter={linkCharacter}
          onCopyCampaign={handleCopyCampaign}
          onDelete={() => setConfirm({ kind: 'campaign', id: state.selected!.id, name: state.selected!.name })}
          onDeleteAdventure={(id) => {
            const adv = state.campaignAdventures.find((a) => a.id === id);
            setConfirm({ kind: 'adventure', id, name: adv?.name || id });
          }}
        />
      )}
    </m.div>
  );
}
