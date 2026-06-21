import { useCallback, useRef, type Dispatch } from 'react';
import type { NavigateFunction } from 'react-router-dom';
import { api } from '../../api/client';
import { type CampaignsAction, type CampaignsState, type CampaignTab } from './campaignsState';

export function useCampaignsPageActions(
  state: CampaignsState,
  dispatch: Dispatch<CampaignsAction>,
  confirm: { kind: 'campaign'; id: string; name: string } | { kind: 'adventure'; id: string; name: string } | null,
  setConfirm: (value: typeof confirm) => void,
  setDeleting: (value: boolean) => void,
  navigate: NavigateFunction,
) {
  const load = useCallback(async () => {
    const [res, chars, advs] = await Promise.all([api.listCampaigns(), api.listCharacters(), api.listAdventures()]);
    dispatch({
      type: 'set',
      patch: {
        campaigns: res.campaigns,
        characters: chars.characters,
        allAdventures: advs.adventures,
        campaignsLoaded: true,
      },
    });
  }, [dispatch]);

  const loadAdventures = useCallback(
    async (campaignId: string) => {
      dispatch({ type: 'set', patch: { adventuresLoaded: false } });
      const res = await api.listCampaignAdventures(campaignId);
      dispatch({ type: 'set', patch: { campaignAdventures: res.adventures, adventuresLoaded: true } });
    },
    [dispatch],
  );

  const charactersRef = useRef(state.characters);
  charactersRef.current = state.characters;
  const inflightOpenRef = useRef<Map<string, Promise<void>>>(new Map());

  const open = useCallback(
    async (id: string, force = false) => {
      if (force) inflightOpenRef.current.delete(id);

      const inflight = inflightOpenRef.current.get(id);
      if (inflight) return inflight;

      const promise = (async () => {
        dispatch({ type: 'set', patch: { entry: null, newAdventureOpen: false, copyOpen: false } });
        const { campaign } = await api.getCampaign(id);
        const defaultChar = campaign.character_ids?.[0] || charactersRef.current[0]?.id || '';
        dispatch({
          type: 'set',
          patch: {
            selected: campaign,
            copyForm: { character_id: defaultChar, name: '' },
          },
        });
        dispatch({ type: 'patchAdventureForm', patch: { character_id: defaultChar } });
        await loadAdventures(id);
      })();

      inflightOpenRef.current.set(id, promise);
      try {
        await promise;
      } finally {
        if (inflightOpenRef.current.get(id) === promise) {
          inflightOpenRef.current.delete(id);
        }
      }
    },
    [dispatch, loadAdventures],
  );

  const create = async (): Promise<string | null> => {
    dispatch({ type: 'set', patch: { error: null } });
    try {
      const res = await api.createCampaign(state.form);
      dispatch({ type: 'set', patch: { selected: res.campaign, creating: false, form: { name: '', story_arc: '' } } });
      await load();
      await loadAdventures(res.id);
      return res.id;
    } catch (e) {
      dispatch({ type: 'set', patch: { error: String(e) } });
      return null;
    }
  };

  const generateFormRef = useRef(state.generateForm);
  generateFormRef.current = state.generateForm;

  const openCreateForm = useCallback(() => {
    const defaultChar = generateFormRef.current.character_id || charactersRef.current[0]?.id || '';
    dispatch({
      type: 'set',
      patch: {
        creating: true,
        generateForm: { ...generateFormRef.current, character_id: defaultChar },
      },
    });
  }, [dispatch]);

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
          generateForm: { ...generateForm, theme: '', campaign_name: '' },
        },
      });
      await load();
      await loadAdventures(result.campaign_id);
      navigate(`/campaigns/${result.campaign_id}/adventures`);
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
    await open(selected.id, true);
    dispatch({ type: 'set', patch: { entry: null } });
  };

  const onTabChange = (tab: CampaignTab) => {
    dispatch({ type: 'set', patch: { tab, entry: null, newAdventureOpen: false } });
  };

  const linkCharacter = async (characterId: string) => {
    if (!state.selected || !characterId) return;
    dispatch({ type: 'set', patch: { error: null, linkingCharacter: true } });
    try {
      const { campaign } = await api.updateCampaign(state.selected.id, { character_ids: [characterId] });
      dispatch({
        type: 'set',
        patch: {
          selected: campaign,
          adventureForm: { ...state.adventureForm, character_id: characterId },
        },
      });
      await load();
    } catch (e) {
      dispatch({ type: 'set', patch: { error: e instanceof Error ? e.message : 'Failed to link character' } });
    } finally {
      dispatch({ type: 'set', patch: { linkingCharacter: false } });
    }
  };

  const copyCampaign = async (): Promise<string | null> => {
    if (!state.selected || !state.copyForm.character_id) return null;
    dispatch({ type: 'set', patch: { error: null, copyingCampaign: true } });
    try {
      const result = await api.copyCampaign(state.selected.id, {
        character_id: state.copyForm.character_id,
        name: state.copyForm.name.trim(),
      });
      await load();
      dispatch({
        type: 'set',
        patch: {
          selected: result.campaign,
          copyOpen: false,
          copyForm: { character_id: state.copyForm.character_id, name: '' },
        },
      });
      await loadAdventures(result.campaign_id);
      return result.campaign_id;
    } catch (e) {
      dispatch({
        type: 'set',
        patch: { error: e instanceof Error ? e.message : 'Failed to copy campaign' },
      });
      return null;
    } finally {
      dispatch({ type: 'set', patch: { copyingCampaign: false } });
    }
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

  return {
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
  };
}
