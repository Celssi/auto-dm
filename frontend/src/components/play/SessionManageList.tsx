import { useState } from 'react';
import { Swords } from 'lucide-react';
import EmptyState from '../ui/EmptyState';
import ListLoading from '../ui/ListLoading';
import OverflowMenu from '../ui/OverflowMenu';
import TextInput from '../ui/forms/TextInput';
import { sessionDisplayTitle, sessionListSubtitle } from '../../lib/displayText';

export interface ManageableSession {
  id: string;
  name: string;
  character_id?: string;
  archived?: boolean;
  created_at?: string;
}

interface Props {
  metaLoaded: boolean;
  sessions: ManageableSession[];
  characters?: { id: string; name: string }[];
  onNavigateSession: (id: string) => void;
  onRenameSession: (id: string, name: string) => Promise<void>;
  onArchiveSession: (id: string, archived: boolean) => Promise<void>;
}

export default function SessionManageList({
  metaLoaded,
  sessions,
  characters = [],
  onNavigateSession,
  onRenameSession,
  onArchiveSession,
}: Props) {
  const [showArchived, setShowArchived] = useState(false);
  const [editingId, setEditingId] = useState('');
  const [draft, setDraft] = useState('');
  const [busyId, setBusyId] = useState('');

  if (!metaLoaded) return <ListLoading />;

  const active = sessions.filter((session) => !session.archived);
  const archived = sessions.filter((session) => session.archived);
  const visible = showArchived ? sessions : active;

  if (sessions.length === 0) {
    return (
      <EmptyState
        icon={<Swords size={28} />}
        title="No sessions yet"
        description="Start a new campaign below to begin your adventure."
      />
    );
  }

  const startRename = (session: ManageableSession) => {
    setEditingId(session.id);
    setDraft(session.name);
  };

  const commitRename = async (id: string) => {
    const name = draft.trim();
    if (!name) return;
    setBusyId(id);
    try {
      await onRenameSession(id, name);
      setEditingId('');
    } finally {
      setBusyId('');
    }
  };

  const toggleArchive = async (session: ManageableSession) => {
    setBusyId(session.id);
    try {
      await onArchiveSession(session.id, !session.archived);
    } finally {
      setBusyId('');
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="label-text">Recent sessions</p>
        {archived.length > 0 && (
          <button
            type="button"
            className="text-xs text-muted hover:text-accent"
            onClick={() => setShowArchived((value) => !value)}
          >
            {showArchived ? 'Hide archived' : `Show archived (${archived.length})`}
          </button>
        )}
      </div>
      {visible.length === 0 ? (
        <p className="text-sm text-muted">All sessions are archived. Turn on Show archived to restore one.</p>
      ) : (
        <ul className="space-y-2">
          {visible.map((session) => {
            const title = sessionDisplayTitle(session.name);
            const characterName = characters.find((character) => character.id === session.character_id)?.name;
            const detail = [sessionListSubtitle(characterName, session.created_at), session.archived ? 'Archived' : '']
              .filter(Boolean)
              .join(' · ');
            return (
              <li key={session.id}>
                {editingId === session.id ? (
                  <form
                    className="flex items-center gap-2 py-3 px-3 rounded-xl border border-border bg-bg/40"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void commitRename(session.id);
                    }}
                  >
                    <TextInput
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      aria-label="Session name"
                      className="flex-1"
                      autoFocus
                    />
                    <button
                      type="submit"
                      className="btn-primary text-xs min-h-9 px-3"
                      disabled={busyId === session.id || !draft.trim()}
                    >
                      Save
                    </button>
                    <button type="button" className="btn-ghost text-xs min-h-9 px-3" onClick={() => setEditingId('')}>
                      Cancel
                    </button>
                  </form>
                ) : (
                  <div className="flex items-center gap-1 py-3 px-3 rounded-xl border border-border bg-bg/40 hover:bg-accent/10 hover:border-accent/30 transition-colors">
                    <button
                      type="button"
                      className="flex-1 text-left min-w-0"
                      onClick={() => onNavigateSession(session.id)}
                    >
                      <span className="block text-sm text-gray-100">{title}</span>
                      {detail && <span className="block text-xs text-muted mt-0.5">{detail}</span>}
                    </button>
                    <OverflowMenu
                      label={`More actions for ${title}`}
                      items={[
                        { label: 'Rename', onSelect: () => startRename(session) },
                        {
                          label: session.archived ? 'Unarchive' : 'Archive',
                          onSelect: () => {
                            void toggleArchive(session);
                          },
                        },
                      ]}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
