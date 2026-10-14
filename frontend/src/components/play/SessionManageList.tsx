import { useState } from 'react';
import { Archive, ArchiveRestore, Pencil, Swords } from 'lucide-react';
import EmptyState from '../ui/EmptyState';
import ListLoading from '../ui/ListLoading';
import TextInput from '../ui/forms/TextInput';

export interface ManageableSession {
  id: string;
  name: string;
  archived?: boolean;
}

interface Props {
  metaLoaded: boolean;
  sessions: ManageableSession[];
  onNavigateSession: (id: string) => void;
  onRenameSession: (id: string, name: string) => Promise<void>;
  onArchiveSession: (id: string, archived: boolean) => Promise<void>;
}

export default function SessionManageList({
  metaLoaded,
  sessions,
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
        <ul className="space-y-1">
          {visible.map((session) => (
            <li
              key={session.id}
              className="rounded-lg border border-transparent hover:border-accent/20 hover:bg-accent/10 px-2 py-1.5"
            >
              {editingId === session.id ? (
                <form
                  className="flex items-center gap-2"
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
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    className="flex-1 text-left py-1.5 px-1 text-sm rounded-md hover:text-accent"
                    onClick={() => onNavigateSession(session.id)}
                  >
                    <span className="block">{session.name}</span>
                    {session.archived && (
                      <span className="text-[10px] uppercase tracking-wider text-muted">Archived</span>
                    )}
                  </button>
                  <button
                    type="button"
                    className="btn-ghost min-h-9 px-2 text-muted"
                    aria-label={`Rename ${session.name}`}
                    onClick={() => startRename(session)}
                    disabled={busyId === session.id}
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    className="btn-ghost min-h-9 px-2 text-muted"
                    aria-label={session.archived ? `Unarchive ${session.name}` : `Archive ${session.name}`}
                    onClick={() => void toggleArchive(session)}
                    disabled={busyId === session.id}
                  >
                    {session.archived ? <ArchiveRestore size={14} /> : <Archive size={14} />}
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
