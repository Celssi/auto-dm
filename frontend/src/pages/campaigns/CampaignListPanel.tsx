import { BookOpen } from 'lucide-react';
import ListCard from '../../components/ui/ListCard';
import EmptyState from '../../components/ui/EmptyState';
import ListLoading from '../../components/ui/ListLoading';
import { campaignCharacterLabel } from '../../lib/displayText';
import type { CampaignsState } from './campaignsState';

interface Props {
  state: CampaignsState;
  onOpen: (id: string) => void;
  onOpenCreateForm: () => void;
}

export default function CampaignListPanel({ state, onOpen, onOpenCreateForm }: Props) {
  if (!state.campaignsLoaded) {
    return <ListLoading />;
  }

  if (state.campaigns.length === 0) {
    return (
      <EmptyState
        icon={<BookOpen size={32} />}
        title="No campaigns yet"
        description="Create a campaign to track your story arc, NPCs, and locations."
        action={
          <button type="button" className="btn-primary" onClick={onOpenCreateForm}>
            New campaign
          </button>
        }
      />
    );
  }

  return (
    <>
      {state.campaigns.map((c) => (
        <ListCard
          key={c.id}
          title={c.name}
          subtitle={campaignCharacterLabel(
            c.character_ids,
            state.characters,
            state.allAdventures.filter((a) => a.campaign_id === c.id),
          )}
          selected={state.selected?.id === c.id}
          onClick={() => onOpen(c.id)}
        />
      ))}
    </>
  );
}
