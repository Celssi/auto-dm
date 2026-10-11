import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { m, AnimatePresence } from '../../lib/framer';
import { MessageSquare, Swords, UserRound, Wrench } from 'lucide-react';
import type { ChatMessage, PlayerProgress, SpellConfirmation } from '../../api/client';
import type { Character } from '../../types';
import PlayCharacterSidebar from '../../components/play/PlayCharacterSidebar';
import PlayToolsPanel from '../../components/play/PlayToolsPanel';
import ListLoading from '../../components/ui/ListLoading';
import { fadeUp } from '../../components/ui/motion';
import { displayLabel } from '../../lib/displayText';
import AnimatedPage from '../../components/ui/AnimatedPage';
import ChatMarkdown from '../../components/play/ChatMarkdown';
import { getGamePlayConfig } from '../../games/play/registry';
import type { PlayState, DiceModalState } from './playState';
import type { JournalEntity } from '../../api/client';
import DiceRollModal from '../../components/play/DiceRollModal';
import SegmentedControl from '../../components/ui/forms/SegmentedControl';
import { useViewport } from '../../hooks/useViewport';

type PlayPane = 'chat' | 'sheet' | 'tools';
type TabletSide = 'sheet' | 'tools';

interface Props {
  state: PlayState;
  bottomRef: React.RefObject<HTMLDivElement | null>;
  onBegin: () => void;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onConfirmSpellCast: () => void;
  onCancelSpellCast: () => void;
  onRunOracle: (id: string) => void;
  onRunShortcut: (id: string) => void;
  onStartNextAdventure: () => void;
  onDiceModalUpdate: (patch: Partial<DiceModalState>) => void;
  onDiceModalSubmit: (preRolled?: number[]) => void;
  onDiceModalClose: () => void;
  onJourneyApply: (index: number) => Promise<{ summary?: string; item_error?: string | null }>;
  onJourneyDrawItem: (index: number) => Promise<{ item_error?: string | null }>;
  onJourneyFinish: () => Promise<void>;
  onJourneyDiscard: () => Promise<void>;
  onJourneyStartCombat: (index: number) => Promise<void>;
  onDragonkeepAction: (action: string) => Promise<void>;
  onDragonkeepInit: () => Promise<void>;
  onBrambletrekCombatAction: (action: string, handIndex?: number) => Promise<void>;
  onCombatAction: (action: string, targetId?: string) => Promise<void>;
}

export default function PlaySessionView({
  state,
  bottomRef,
  onBegin,
  onInputChange,
  onSend,
  onConfirmSpellCast,
  onCancelSpellCast,
  onRunOracle,
  onRunShortcut,
  onStartNextAdventure,
  onDiceModalUpdate,
  onDiceModalSubmit,
  onDiceModalClose,
  onJourneyApply,
  onJourneyDrawItem,
  onJourneyFinish,
  onJourneyDiscard,
  onJourneyStartCombat,
  onDragonkeepAction,
  onDragonkeepInit,
  onBrambletrekCombatAction,
  onCombatAction,
}: Props) {
  const {
    sessionLoaded,
    loadError,
    messages,
    loading,
    beginning,
    beginError,
    character,
    characterId,
    characterSummary,
    input,
    chatError,
    spellConfirm,
    oracles,
    shortcuts,
    lonelog,
    auditEvents,
    sources,
    journalEntities,
    playerProgress,
    adventureComplete,
    nextAdventure,
    startingNext,
    campaignId,
    combatState,
    brambletrekCombat,
    diceModal,
    pendingJourney,
    dragonkeep,
    sessionId,
  } = state;

  const activeAdventure = String(character?.active_adventure ?? '');

  const gameId = character?.game_id ?? 'dnd5e';
  const playConfig = getGamePlayConfig(gameId);
  const panes = usePlayPanes();

  return (
    <AnimatedPage className="flex-1 min-h-0 h-full flex flex-col gap-2 overflow-hidden">
      <PlaySessionLayout
        viewport={panes.viewport}
        showSheet={panes.showSheet}
        showChat={panes.showChat}
        showTools={panes.showTools}
        tabletSide={panes.tabletSide}
        phonePane={panes.phonePane}
        onTabletSide={panes.setTabletSide}
        onPhonePane={panes.setPhonePane}
        sheet={
          <PlayCharacterPanel
            character={character}
            characterId={characterId}
            characterSummary={characterSummary}
            playerProgress={playerProgress}
          />
        }
        chat={
          <main className="panel-glow flex flex-col min-h-0 overflow-hidden flex-1">
            <PlayChatArea
              sessionLoaded={sessionLoaded}
              loadError={loadError}
              messages={messages}
              loading={loading}
              beginning={beginning}
              beginError={beginError}
              onBegin={onBegin}
              journalEntities={journalEntities}
              bottomRef={bottomRef}
              adventureComplete={adventureComplete}
              nextAdventure={nextAdventure}
              playerProgress={playerProgress}
              startingNext={startingNext}
              campaignId={campaignId}
              onStartNextAdventure={onStartNextAdventure}
            />
            <PlayChatInput
              input={input}
              loading={loading}
              chatError={chatError}
              spellConfirm={spellConfirm}
              onInputChange={onInputChange}
              onSend={onSend}
              onConfirmSpellCast={onConfirmSpellCast}
              onCancelSpellCast={onCancelSpellCast}
            />
          </main>
        }
        tools={
          <PlayToolsPanel
            gameId={gameId}
            sessionId={sessionId}
            characterId={characterId}
            pendingJourney={pendingJourney}
            dragonkeep={dragonkeep}
            activeAdventure={activeAdventure}
            oracles={oracles}
            shortcuts={shortcuts}
            lonelog={lonelog}
            auditEvents={auditEvents}
            sources={sources}
            loading={loading}
            combatState={combatState}
            brambletrekCombat={brambletrekCombat}
            onRunOracle={onRunOracle}
            onRunShortcut={onRunShortcut}
            onJourneyApply={onJourneyApply}
            onJourneyDrawItem={onJourneyDrawItem}
            onJourneyFinish={onJourneyFinish}
            onJourneyDiscard={onJourneyDiscard}
            onJourneyStartCombat={onJourneyStartCombat}
            onDragonkeepAction={onDragonkeepAction}
            onDragonkeepInit={onDragonkeepInit}
            onBrambletrekCombatAction={onBrambletrekCombatAction}
            onCombatAction={onCombatAction}
          />
        }
      />

      <AnimatePresence>
        {diceModal && character && playConfig.usesDiceModal && (
          <DiceRollModal
            modal={diceModal}
            abilityScores={character.ability_scores ?? {}}
            saveProficiencies={character.save_proficiencies ?? []}
            level={character.level}
            onUpdate={onDiceModalUpdate}
            onSubmit={onDiceModalSubmit}
            onClose={onDiceModalClose}
          />
        )}
      </AnimatePresence>
    </AnimatedPage>
  );
}

function usePlayPanes() {
  const viewport = useViewport();
  const [phonePane, setPhonePane] = useState<PlayPane>('chat');
  const [tabletSide, setTabletSide] = useState<TabletSide>('tools');
  return {
    viewport,
    phonePane,
    tabletSide,
    setPhonePane,
    setTabletSide,
    showSheet:
      viewport === 'desktop' ||
      (viewport === 'tablet' && tabletSide === 'sheet') ||
      (viewport === 'phone' && phonePane === 'sheet'),
    showChat: viewport !== 'phone' || phonePane === 'chat',
    showTools:
      viewport === 'desktop' ||
      (viewport === 'tablet' && tabletSide === 'tools') ||
      (viewport === 'phone' && phonePane === 'tools'),
  };
}

function PlaySessionLayout({
  viewport,
  showSheet,
  showChat,
  showTools,
  tabletSide,
  phonePane,
  onTabletSide,
  onPhonePane,
  sheet,
  chat,
  tools,
}: {
  viewport: ReturnType<typeof useViewport>;
  showSheet: boolean;
  showChat: boolean;
  showTools: boolean;
  tabletSide: TabletSide;
  phonePane: PlayPane;
  onTabletSide: (value: TabletSide) => void;
  onPhonePane: (value: PlayPane) => void;
  sheet: ReactNode;
  chat: ReactNode;
  tools: ReactNode;
}) {
  const columns = viewport === 'desktop' ? 'grid-cols-12' : viewport === 'tablet' ? 'grid-cols-2' : 'grid-cols-1';
  return (
    <>
      <div className={`flex-1 min-h-0 grid gap-3 overflow-hidden ${columns}`}>
        {viewport === 'desktop' && showSheet && <div className="col-span-3 min-h-0 flex flex-col">{sheet}</div>}
        {viewport === 'phone' && showSheet && <div className="min-h-0 flex flex-col">{sheet}</div>}
        {showChat && (
          <div className={`min-h-0 flex flex-col ${viewport === 'desktop' ? 'col-span-6' : ''}`}>{chat}</div>
        )}
        {viewport === 'tablet' && (
          <div className="min-h-0 flex flex-col gap-2">
            <SegmentedControl
              value={tabletSide}
              onChange={(value) => onTabletSide(value as TabletSide)}
              options={[
                { value: 'sheet', label: 'Sheet' },
                { value: 'tools', label: 'Tools' },
              ]}
            />
            <div className="flex-1 min-h-0 flex flex-col">{tabletSide === 'sheet' ? sheet : tools}</div>
          </div>
        )}
        {viewport !== 'tablet' && showTools && (
          <div className={`min-h-0 flex flex-col ${viewport === 'desktop' ? 'col-span-3' : ''}`}>{tools}</div>
        )}
      </div>
      {viewport === 'phone' && <PlayPaneBar active={phonePane} onChange={onPhonePane} />}
    </>
  );
}

function PlayPaneBar({ active, onChange }: { active: PlayPane; onChange: (pane: PlayPane) => void }) {
  const panes: { id: PlayPane; label: string; icon: typeof MessageSquare }[] = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'sheet', label: 'Sheet', icon: UserRound },
    { id: 'tools', label: 'Tools', icon: Wrench },
  ];
  return (
    <div className="shrink-0 grid grid-cols-3 rounded-xl border border-border bg-panel/80">
      {panes.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          type="button"
          className={`min-h-12 inline-flex flex-col items-center justify-center gap-0.5 text-[11px] ${
            active === id ? 'text-accent' : 'text-muted'
          }`}
          onClick={() => onChange(id)}
        >
          <Icon size={18} />
          {label}
        </button>
      ))}
    </div>
  );
}

function PlayCharacterPanel({
  character,
  characterId,
  characterSummary,
  playerProgress,
}: {
  character: Character | null;
  characterId: string;
  characterSummary: Record<string, unknown>;
  playerProgress: PlayerProgress | null;
}) {
  const completed = playerProgress?.completed_beats ?? [];
  return (
    <aside className="panel-glow overflow-y-auto p-3 flex flex-col gap-3 min-h-0 flex-1">
      <div className="flex items-center justify-between gap-2 shrink-0">
        <h2 className="section-heading">Character</h2>
        {character && characterId && (
          <Link
            to={`/characters/${characterId}`}
            className="text-[10px] text-accent/80 hover:text-accent hover:underline"
          >
            Full sheet
          </Link>
        )}
      </div>
      {character ? (
        <PlayCharacterSidebar character={character} summary={characterSummary} />
      ) : (
        <p className="text-sm text-muted">Loading…</p>
      )}
      <div className="rounded-lg border border-border bg-bg/40 p-3 space-y-2 shrink-0">
        <p className="section-heading">Story so far</p>
        {playerProgress?.adventure_complete ? (
          <p className="text-sm text-accent">Adventure complete.</p>
        ) : playerProgress?.stage ? (
          <p className="text-sm text-muted">{playerProgress.stage}</p>
        ) : (
          <p className="text-sm text-muted italic">Play to discover what happens next.</p>
        )}
        {completed.length > 0 ? (
          <ul className="text-xs text-gray-300 space-y-1 list-disc list-inside">
            {completed.map((beat) => (
              <li key={beat}>{beat}</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted italic">No beats completed yet.</p>
        )}
        <p className="text-[10px] text-muted leading-relaxed">The DM knows more than you see here.</p>
      </div>
    </aside>
  );
}

function PlayChatArea({
  sessionLoaded,
  loadError,
  messages,
  loading,
  beginning,
  beginError,
  onBegin,
  journalEntities,
  bottomRef,
  adventureComplete,
  nextAdventure,
  playerProgress,
  startingNext,
  campaignId,
  onStartNextAdventure,
}: {
  sessionLoaded: boolean;
  loadError: string;
  messages: ChatMessage[];
  loading: boolean;
  beginning: boolean;
  beginError: string;
  onBegin: () => void;
  journalEntities: JournalEntity[];
  bottomRef: React.RefObject<HTMLDivElement | null>;
  adventureComplete: boolean;
  nextAdventure: { id: string; name: string } | null;
  playerProgress: PlayerProgress | null;
  startingNext: boolean;
  campaignId: string;
  onStartNextAdventure: () => void;
}) {
  if (!sessionLoaded) {
    return (
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4 scroll-smooth min-h-0">
        <div className="flex flex-col items-center justify-center h-full min-h-[12rem]">
          <ListLoading />
        </div>
      </div>
    );
  }
  if (loadError) {
    return (
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4 scroll-smooth min-h-0">
        <div className="flex flex-col items-center justify-center h-full min-h-[12rem] text-center px-6">
          <p className="text-sm text-danger rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 max-w-md">
            {loadError}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4 scroll-smooth min-h-0">
      <>
        <ChatReadyPrompt
          show={messages.length === 0 && !loading && !beginning}
          beginError={beginError}
          onBegin={onBegin}
        />
        <ChatBeginning show={beginning} />
        <AdventureCompleteBanner
          show={adventureComplete}
          playerProgress={playerProgress}
          nextAdventure={nextAdventure}
          startingNext={startingNext}
          campaignId={campaignId}
          onStartNextAdventure={onStartNextAdventure}
        />
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <m.div
              key={`${msg.role}-${msg.content.length}-${msg.content.slice(0, 48)}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[92%] rounded-xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-accent/15 border border-accent/25 text-gray-100'
                    : 'bg-bg/80 border border-border border-l-2 border-l-accent/60'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="text-[10px] uppercase tracking-wider text-accent/70 mb-1.5 font-medium">DM</div>
                )}
                <ChatMarkdown content={msg.content} entities={journalEntities} />
              </div>
            </m.div>
          ))}
        </AnimatePresence>
        {loading && (
          <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
            <div className="rounded-xl px-4 py-3 bg-bg/80 border border-border border-l-2 border-l-accent/60">
              <p className="text-sm text-muted animate-pulse">DM is thinking…</p>
            </div>
          </m.div>
        )}
        <div ref={bottomRef} />
      </>
    </div>
  );
}

function ChatReadyPrompt({ show, beginError, onBegin }: { show: boolean; beginError: string; onBegin: () => void }) {
  if (!show) return null;
  return (
    <m.div
      variants={fadeUp}
      initial="initial"
      animate="animate"
      className="flex flex-col items-center justify-center h-full min-h-[12rem] text-center px-6"
    >
      <Swords className="text-accent/40 mb-4" size={36} />
      <p className="display-title text-lg">Ready to begin</p>
      <p className="text-sm text-muted mt-2 max-w-md mb-5">
        The DM will write the opening scene and drop you into the action.
      </p>
      {beginError && (
        <p className="text-sm text-danger rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 mb-4 max-w-md">
          {beginError}
        </p>
      )}
      <button type="button" className="btn-primary px-6 py-2.5" onClick={onBegin}>
        Begin adventure
      </button>
    </m.div>
  );
}

function ChatBeginning({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <m.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center min-h-[12rem] text-center px-6"
    >
      <Swords className="text-accent/40 mb-4 animate-pulse" size={36} />
      <p className="display-title text-lg">Setting the scene…</p>
      <p className="text-sm text-muted mt-2">Writing the opening scene (30-60 s)</p>
    </m.div>
  );
}

function AdventureCompleteBanner({
  show,
  playerProgress,
  nextAdventure,
  startingNext,
  campaignId,
  onStartNextAdventure,
}: {
  show: boolean;
  playerProgress: PlayerProgress | null;
  nextAdventure: { id: string; name: string } | null;
  startingNext: boolean;
  campaignId: string;
  onStartNextAdventure: () => void;
}) {
  if (!show) return null;
  const beats = playerProgress?.completed_beats ?? [];
  return (
    <m.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-4 space-y-3"
    >
      <p className="font-display text-lg text-accent">Adventure complete</p>
      {beats.length > 0 && (
        <ul className="text-sm text-gray-300 space-y-1 list-disc list-inside">
          {beats.map((beat) => (
            <li key={beat}>{beat}</li>
          ))}
        </ul>
      )}
      {nextAdventure ? (
        <button type="button" className="btn-primary text-sm" onClick={onStartNextAdventure} disabled={startingNext}>
          {startingNext ? 'Starting next adventure…' : `Start: ${nextAdventure.name}`}
        </button>
      ) : campaignId ? (
        <Link to={`/campaigns/${campaignId}`} className="text-sm text-accent hover:underline">
          View campaign adventures
        </Link>
      ) : null}
    </m.div>
  );
}

function PlayChatInput({
  input,
  loading,
  chatError,
  spellConfirm,
  onInputChange,
  onSend,
  onConfirmSpellCast,
  onCancelSpellCast,
}: {
  input: string;
  loading: boolean;
  chatError: string;
  spellConfirm: SpellConfirmation | null;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onConfirmSpellCast: () => void;
  onCancelSpellCast: () => void;
}) {
  return (
    <div className="border-t border-border p-3 space-y-2 shrink-0 bg-panel/50">
      {chatError && (
        <p className="text-sm text-danger rounded-lg border border-danger/30 bg-danger/10 px-3 py-2">{chatError}</p>
      )}
      {spellConfirm && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm">
          <p className="text-muted mb-2">
            Cast <span className="font-semibold text-gray-100">{displayLabel(spellConfirm.suggested)}</span> (you wrote
            “{displayLabel(spellConfirm.requested)}”)?
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-primary text-xs" onClick={onConfirmSpellCast} disabled={loading}>
              Cast {displayLabel(spellConfirm.suggested)}
            </button>
            <button type="button" className="btn-ghost text-xs" onClick={onCancelSpellCast} disabled={loading}>
              No, narrative only
            </button>
          </div>
        </div>
      )}
      <div className="flex gap-2">
        <input
          className="input flex-1 py-2.5 text-base"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && onSend()}
          placeholder="What do you do?"
          aria-label="Message to the DM"
          disabled={loading}
        />
        <button
          type="button"
          className="btn-primary px-5 py-2.5 shrink-0"
          onClick={onSend}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
