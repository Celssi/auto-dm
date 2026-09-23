import { api, type BootstrapCampaignResult } from '../../api/client';

export async function bootstrapBrambletrekSession(opts: {
  characterId: string;
  activeAdventure?: string;
  campaignName?: string;
  flavorNotes?: string;
}): Promise<BootstrapCampaignResult> {
  const { character } = await api.getCharacter(opts.characterId);
  const char = character as Record<string, unknown>;
  const nextAdventure = opts.activeAdventure ?? String(char.active_adventure || '');
  if (nextAdventure && nextAdventure !== String(char.active_adventure || '')) {
    await api.updateCharacter(opts.characterId, { ...char, active_adventure: nextAdventure });
  }
  return api.bootstrapCampaign({
    character_id: opts.characterId,
    mode: 'module',
    theme: opts.flavorNotes?.trim() || '',
    campaign_name: opts.campaignName?.trim() || '',
  });
}
