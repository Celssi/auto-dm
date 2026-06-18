import { m, AnimatePresence } from '../../lib/framer';
import { Map, Users, Compass, Play, Sparkles } from 'lucide-react';
import type { AdventureMeta, CampaignFull, JournalEntry, ModuleSource } from '../../api/client';
import TabBar from '../../components/ui/TabBar';
import EmptyState from '../../components/ui/EmptyState';
import ListLoading from '../../components/ui/ListLoading';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';
import ChoiceGroup from '../../components/ui/forms/ChoiceGroup';
import SegmentedControl from '../../components/ui/forms/SegmentedControl';
import Toggle from '../../components/ui/forms/Toggle';
import MarkdownContent from '../../components/ui/MarkdownContent';
import type { CampaignTab, CampaignsState } from './campaignsState';

interface Props {
  campaign: CampaignFull;
  state: Pick<
    CampaignsState,
    | 'tab'
    | 'entry'
    | 'campaignAdventures'
    | 'adventuresLoaded'
    | 'characters'
    | 'newAdventureOpen'
    | 'bootstrapping'
    | 'adventureForm'
  >;
  onTabChange: (tab: CampaignTab) => void;
  onOpenEntry: (kind: 'npc' | 'location', id: string) => void;
  onSaveEntry: () => void;
  onSetEntry: (entry: JournalEntry | null) => void;
  onToggleNewAdventure: () => void;
  onPatchAdventureForm: (patch: Partial<CampaignsState['adventureForm']>) => void;
  onStartNewAdventure: () => void;
  onPlayAdventure: (id: string) => void;
  onDelete: () => void;
  onDeleteAdventure: (id: string) => void;
}

export default function CampaignDetailPanel({
  campaign,
  state,
  onTabChange,
  onOpenEntry,
  onSaveEntry,
  onSetEntry,
  onToggleNewAdventure,
  onPatchAdventureForm,
  onStartNewAdventure,
  onPlayAdventure,
  onDelete,
  onDeleteAdventure,
}: Props) {
  const list = state.tab === 'npcs' ? campaign.npcs : state.tab === 'locations' ? campaign.locations : [];
  const tabs = [
    { id: 'story', label: 'Story arc' },
    { id: 'adventures', label: `Adventures (${state.campaignAdventures.length})` },
    { id: 'npcs', label: `NPCs (${campaign.npcs?.length ?? 0})` },
    { id: 'locations', label: `Locations (${campaign.locations?.length ?? 0})` },
  ];

  return (
    <m.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      className="lg:col-span-2 panel-glow p-5 space-y-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="font-display text-xl text-gray-100">{campaign.name}</h2>
        <button type="button" className="btn-danger text-sm" onClick={onDelete}>
          Delete campaign
        </button>
      </div>

      <TabBar tabs={tabs} active={state.tab} onChange={(id) => onTabChange(id as CampaignTab)} />

      <AnimatePresence mode="wait">
        {state.tab === 'story' && (
          <m.div
            key="story"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            {campaign.source_module && <ModuleSourceBadge source={campaign.source_module} />}
            <div className="rounded-lg border border-border bg-bg/40 p-4 max-h-[60vh] overflow-y-auto">
              {campaign.story_arc ? (
                <MarkdownContent content={campaign.story_arc} />
              ) : (
                <p className="text-sm text-muted">No story arc yet.</p>
              )}
            </div>
          </m.div>
        )}

        {state.tab === 'adventures' && (
          <CampaignAdventuresTab
            adventures={state.campaignAdventures}
            adventuresLoaded={state.adventuresLoaded}
            characters={state.characters}
            newAdventureOpen={state.newAdventureOpen}
            bootstrapping={state.bootstrapping}
            adventureForm={state.adventureForm}
            onToggleNewAdventure={onToggleNewAdventure}
            onPatchAdventureForm={onPatchAdventureForm}
            onStartNewAdventure={onStartNewAdventure}
            onPlayAdventure={onPlayAdventure}
            onDeleteAdventure={onDeleteAdventure}
          />
        )}

        {state.tab !== 'story' && state.tab !== 'adventures' && !state.entry && (
          <CampaignJournalList tab={state.tab} list={list || []} onOpenEntry={onOpenEntry} />
        )}

        {state.entry && <CampaignEntryEditor entry={state.entry} onSetEntry={onSetEntry} onSaveEntry={onSaveEntry} />}
      </AnimatePresence>
    </m.div>
  );
}

function CampaignAdventuresTab({
  adventures,
  adventuresLoaded,
  characters,
  newAdventureOpen,
  bootstrapping,
  adventureForm,
  onToggleNewAdventure,
  onPatchAdventureForm,
  onStartNewAdventure,
  onPlayAdventure,
  onDeleteAdventure,
}: {
  adventures: AdventureMeta[];
  adventuresLoaded: boolean;
  characters: { id: string; name: string }[];
  newAdventureOpen: boolean;
  bootstrapping: boolean;
  adventureForm: CampaignsState['adventureForm'];
  onToggleNewAdventure: () => void;
  onPatchAdventureForm: (patch: Partial<CampaignsState['adventureForm']>) => void;
  onStartNewAdventure: () => void;
  onPlayAdventure: (id: string) => void;
  onDeleteAdventure: (id: string) => void;
}) {
  return (
    <m.div
      key="adventures"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted">
          Each adventure keeps its own log and canon. The DM remembers prior adventures when you start a new one.
        </p>
        <button
          type="button"
          className="btn-primary text-sm inline-flex items-center gap-1.5 shrink-0"
          onClick={onToggleNewAdventure}
        >
          <Sparkles size={14} />
          {newAdventureOpen ? 'Cancel' : 'New adventure'}
        </button>
      </div>

      <AnimatePresence>
        {newAdventureOpen && (
          <m.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="rounded-lg border border-accent/25 bg-accent/5 p-4 space-y-4 overflow-hidden"
          >
            <Field label="Character">
              <ChoiceGroup
                value={adventureForm.character_id}
                onChange={(character_id) => onPatchAdventureForm({ character_id })}
                options={characters.map((c) => ({ value: c.id, label: c.name }))}
                columns={2}
              />
            </Field>
            <Field label="Adventure type">
              <SegmentedControl
                value={adventureForm.mode}
                onChange={(mode) => onPatchAdventureForm({ mode: mode as 'freeform' | 'module' })}
                options={[
                  { value: 'freeform', label: 'Freeform' },
                  { value: 'module', label: 'Module' },
                ]}
              />
            </Field>
            <Toggle
              checked={adventureForm.auto_continue}
              onChange={(auto_continue) =>
                onPatchAdventureForm({ auto_continue, theme: auto_continue ? '' : adventureForm.theme })
              }
              label="AI invents what happens next (no theme needed)"
            />
            {!adventureForm.auto_continue && (
              <Field label="Theme / hook">
                <TextArea
                  placeholder="What happens next in the campaign?"
                  value={adventureForm.theme}
                  onChange={(e) => onPatchAdventureForm({ theme: e.target.value })}
                  className="min-h-[80px]"
                />
              </Field>
            )}
            <Field label="Adventure name (optional)">
              <TextInput
                placeholder="e.g. The Seal Beneath the Tower"
                value={adventureForm.adventure_name}
                onChange={(e) => onPatchAdventureForm({ adventure_name: e.target.value })}
              />
            </Field>
            <Toggle
              checked={adventureForm.include_faerun}
              onChange={(include_faerun) => onPatchAdventureForm({ include_faerun })}
              label="Use Faerûn supplements"
            />
            <button
              type="button"
              className="btn-primary w-full py-2.5"
              disabled={
                !adventureForm.character_id ||
                (!adventureForm.auto_continue && !adventureForm.theme.trim()) ||
                bootstrapping
              }
              onClick={onStartNewAdventure}
            >
              {bootstrapping
                ? adventureForm.auto_continue
                  ? 'Inventing next adventure… (30-60 s)'
                  : 'Generating adventure… (30-60 s)'
                : adventureForm.auto_continue
                  ? 'Invent & play'
                  : 'Generate & play'}
            </button>
          </m.div>
        )}
      </AnimatePresence>

      {!adventuresLoaded ? (
        <ListLoading />
      ) : adventures.length === 0 ? (
        <EmptyState
          icon={<Compass size={28} />}
          title="No adventures yet"
          description="Start the first adventure in this campaign, or use Play → New campaign to bootstrap one."
        />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {adventures.map((adv) => (
            <li key={adv.id} className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-accent/5">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  {adv.sequence != null && <span className="text-xs text-muted font-mono">#{adv.sequence}</span>}
                  <p className="font-medium text-gray-100 truncate">{adv.name}</p>
                  {adv.status === 'planned' && (
                    <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted/20 text-muted">
                      planned
                    </span>
                  )}
                  {adv.status === 'completed' && (
                    <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-accent/20 text-accent">
                      completed
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted capitalize">{adv.mode || 'freeform'}</p>
                {adv.source_module && (
                  <p className="text-xs text-accent/80 truncate mt-0.5">{formatModuleSource(adv.source_module)}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button type="button" className="btn-danger text-xs" onClick={() => onDeleteAdventure(adv.id)}>
                  Delete
                </button>
                <button
                  type="button"
                  className="btn-primary text-xs inline-flex items-center gap-1 shrink-0"
                  onClick={() => onPlayAdventure(adv.id)}
                  disabled={adv.status === 'completed'}
                >
                  <Play size={12} /> {adv.status === 'planned' ? 'Start' : adv.status === 'completed' ? 'Done' : 'Play'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </m.div>
  );
}

function formatModuleSource(source: ModuleSource): string {
  const parts = [source.title];
  if (source.chapter) parts.push(source.chapter);
  if (source.pages) parts.push(`p. ${source.pages}`);
  if (source.source_label && !parts.includes(source.source_label)) {
    parts.push(`(${source.source_label})`);
  }
  return parts.join(' · ');
}

function ModuleSourceBadge({ source }: { source: ModuleSource }) {
  return (
    <div className="rounded-lg border border-accent/20 bg-accent/5 px-4 py-3 text-sm space-y-1">
      <p className="text-xs uppercase tracking-wide text-muted">Source book</p>
      <p className="text-gray-100 font-medium">{source.title}</p>
      {(source.source_label || source.chapter || source.pages) && (
        <p className="text-xs text-muted">
          {[source.source_label, source.chapter, source.pages ? `p. ${source.pages}` : ''].filter(Boolean).join(' · ')}
        </p>
      )}
      {source.notes && <p className="text-xs text-gray-400 leading-relaxed">{source.notes}</p>}
    </div>
  );
}

function CampaignJournalList({
  tab,
  list,
  onOpenEntry,
}: {
  tab: CampaignTab;
  list: { id: string; name: string }[];
  onOpenEntry: (kind: 'npc' | 'location', id: string) => void;
}) {
  return (
    <m.ul
      key="list"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="divide-y divide-border max-h-[50vh] overflow-y-auto rounded-lg border border-border"
    >
      {list.length === 0 ? (
        <li className="p-6 text-sm text-muted text-center">No {tab === 'npcs' ? 'NPCs' : 'locations'} yet.</li>
      ) : (
        list.map((row) => (
          <li key={row.id}>
            <button
              type="button"
              className="w-full text-left px-4 py-3 hover:bg-accent/5 hover:text-accent transition-colors flex items-center gap-2"
              onClick={() => onOpenEntry(tab === 'npcs' ? 'npc' : 'location', row.id)}
            >
              {tab === 'npcs' ? <Users size={14} className="text-muted" /> : <Map size={14} className="text-muted" />}
              {row.name}
            </button>
          </li>
        ))
      )}
    </m.ul>
  );
}

function CampaignEntryEditor({
  entry,
  onSetEntry,
  onSaveEntry,
}: {
  entry: JournalEntry;
  onSetEntry: (entry: JournalEntry | null) => void;
  onSaveEntry: () => void;
}) {
  return (
    <m.div
      key="entry"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-4"
    >
      <TextInput
        inputClassName="font-display text-lg"
        value={entry.name}
        onChange={(e) => onSetEntry({ ...entry, name: e.target.value })}
      />
      <TextArea
        className="font-mono text-sm min-h-[280px]"
        value={entry.body}
        onChange={(e) => onSetEntry({ ...entry, body: e.target.value })}
      />
      <div className="flex gap-2">
        <button type="button" className="btn-primary" onClick={onSaveEntry}>
          Save
        </button>
        <button type="button" className="btn-ghost" onClick={() => onSetEntry(null)}>
          Back
        </button>
      </div>
    </m.div>
  );
}
