import { DEFAULT_GAME_ID, type GameId } from '../games/registry';
import { resolvedCampaignCharacterIds } from './displayText';

export type CharacterRef = { id: string; name: string; game_id?: string };

export function matchesGame(gameId: string | undefined, active: GameId): boolean {
  return (gameId || DEFAULT_GAME_ID) === active;
}

export function filterByGame<T extends { game_id?: string }>(items: T[], active: GameId): T[] {
  return items.filter((item) => matchesGame(item.game_id, active));
}

export function campaignMatchesGame(
  campaign: { id: string; character_ids?: string[] },
  characters: CharacterRef[],
  adventures: { campaign_id?: string; character_id?: string }[],
  active: GameId,
): boolean {
  const campaignAdventures = adventures.filter((a) => a.campaign_id === campaign.id);
  const ids = resolvedCampaignCharacterIds(campaign.character_ids, campaignAdventures);
  if (ids.length === 0) return active === DEFAULT_GAME_ID;
  return ids.some((id) => {
    const character = characters.find((c) => c.id === id);
    return character ? matchesGame(character.game_id, active) : false;
  });
}

export function sessionMatchesGame(
  session: { character_id?: string },
  characters: CharacterRef[],
  active: GameId,
): boolean {
  if (!session.character_id) return active === DEFAULT_GAME_ID;
  const character = characters.find((c) => c.id === session.character_id);
  return character ? matchesGame(character.game_id, active) : active === DEFAULT_GAME_ID;
}

export function leaveScopedRoute(pathname: string): string | null {
  if (/^\/play\/[^/]+/.test(pathname)) return '/';
  if (/^\/characters\/.+/.test(pathname)) return '/characters';
  if (/^\/campaigns\/.+/.test(pathname)) return '/campaigns';
  if (/^\/adventures\/.+/.test(pathname)) return '/adventures';
  return null;
}
