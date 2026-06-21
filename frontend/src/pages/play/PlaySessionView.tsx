import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { m, AnimatePresence } from '../../lib/framer';
import { Swords } from 'lucide-react';
import type {
  ChatMessage,
  AuditEvent,
  CombatStateSnapshot,
  PlayerProgress,
  Source,
  SpellConfirmation,
} from '../../api/client';
import type { Character } from '../../types';
import PlayCharacterSidebar from '../../components/play/PlayCharacterSidebar';
import ListLoading from '../../components/ui/ListLoading';
import { fadeUp } from '../../components/ui/motion';
import { displayLabel } from '../../lib/displayText';
import AnimatedPage from '../../components/ui/AnimatedPage';
import ChatMarkdown from '../../components/play/ChatMarkdown';
import MarkdownContent from '../../components/ui/MarkdownContent';
import type { PlayState, DiceModalState } from './playState';
import type { JournalEntity } from '../../api/client';
import DiceRollModal from '../../components/play/DiceRollModal';
import { formatAuditSummary, formatAuditTime, isInferredAudit } from './auditSummary';

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
    diceModal,
  } = state;

  return (
    <AnimatedPage className="lg:flex-1 lg:min-h-0 lg:h-full grid grid-cols-1 lg:grid-cols-12 lg:grid-rows-1 gap-3 lg:overflow-hidden">
      <PlayCharacterPanel
        character={character}
        characterId={characterId}
        characterSummary={characterSummary}
        playerProgress={playerProgress}
      />

      <main className="lg:col-span-6 panel-glow flex flex-col min-h-0 overflow-hidden">
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

      <PlayToolsPanel
        oracles={oracles}
        shortcuts={shortcuts}
        lonelog={lonelog}
        auditEvents={auditEvents}
        sources={sources}
        loading={loading}
        combatState={combatState}
        onRunOracle={onRunOracle}
        onRunShortcut={onRunShortcut}
      />

      <AnimatePresence>
        {diceModal && character && (
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
    <aside className="lg:col-span-3 panel-glow overflow-y-auto p-3 flex flex-col gap-3 min-h-0">
      <div className="flex items-center justify-between gap-2 shrink-0">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">Character</h2>
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
        <p className="text-xs font-semibold uppercase tracking-wider text-muted">Story so far</p>
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
  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4 scroll-smooth min-h-0">
      {!sessionLoaded ? (
        <div className="flex flex-col items-center justify-center h-full min-h-[12rem]">
          <ListLoading />
        </div>
      ) : loadError ? (
        <div className="flex flex-col items-center justify-center h-full min-h-[12rem] text-center px-6">
          <p className="text-sm text-danger rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 max-w-md">
            {loadError}
          </p>
        </div>
      ) : (
        <>
          {messages.length === 0 && !loading && !beginning && (
            <m.div
              variants={fadeUp}
              initial="initial"
              animate="animate"
              className="flex flex-col items-center justify-center h-full min-h-[12rem] text-center px-6"
            >
              <Swords className="text-accent/40 mb-4" size={36} />
              <p className="font-display text-lg text-gray-300">Ready to begin</p>
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
          )}
          {beginning && (
            <m.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center min-h-[12rem] text-center px-6"
            >
              <Swords className="text-accent/40 mb-4 animate-pulse" size={36} />
              <p className="font-display text-lg text-gray-300">Setting the scene…</p>
              <p className="text-sm text-muted mt-2">Writing the opening scene (30-60 s)</p>
            </m.div>
          )}
          {adventureComplete && (
            <m.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-4 space-y-3"
            >
              <p className="font-display text-lg text-accent">Adventure complete</p>
              {(playerProgress?.completed_beats ?? []).length > 0 && (
                <ul className="text-sm text-gray-300 space-y-1 list-disc list-inside">
                  {(playerProgress?.completed_beats ?? []).map((beat) => (
                    <li key={beat}>{beat}</li>
                  ))}
                </ul>
              )}
              {nextAdventure ? (
                <button
                  type="button"
                  className="btn-primary text-sm"
                  onClick={onStartNextAdventure}
                  disabled={startingNext}
                >
                  {startingNext ? 'Starting next adventure…' : `Start: ${nextAdventure.name}`}
                </button>
              ) : campaignId ? (
                <Link to={`/campaigns/${campaignId}`} className="text-sm text-accent hover:underline">
                  View campaign adventures
                </Link>
              ) : null}
            </m.div>
          )}
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
      )}
    </div>
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

function visibleLonelogLines(lonelog: string[]): string[] {
  const lines: string[] = [];
  for (const line of lonelog.slice(-24)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (/^#+\s/.test(trimmed)) continue;
    if (/^_.*_$/.test(trimmed)) continue;
    lines.push(line);
  }
  return lines;
}

function PlayToolsPanel({
  oracles,
  shortcuts,
  lonelog,
  auditEvents,
  sources,
  loading,
  combatState,
  onRunOracle,
  onRunShortcut,
}: {
  oracles: { id: string; label: string }[];
  shortcuts: { id: string; label: string }[];
  lonelog: string[];
  auditEvents: AuditEvent[];
  sources: Source[];
  loading: boolean;
  combatState: CombatStateSnapshot | null;
  onRunOracle: (id: string) => void;
  onRunShortcut: (id: string) => void;
}) {
  const [logTab, setLogTab] = useState<'lonelog' | 'audit'>('lonelog');
  const visibleLog = useMemo(() => visibleLonelogLines(lonelog), [lonelog]);
  const visibleAudit = useMemo(() => auditEvents.slice(-30).reverse(), [auditEvents]);

  return (
    <aside className="lg:col-span-3 panel-glow overflow-hidden p-3 min-h-0 flex flex-col gap-2">
      {combatState && combatState.status === 'active' && <CombatPanel state={combatState} />}
      <div className="shrink-0">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">Oracles</h2>
        <div className="grid grid-cols-2 gap-1 max-h-[9rem] overflow-y-auto pr-0.5">
          {oracles.map((o) => (
            <button
              key={o.id}
              type="button"
              className="play-chip text-left"
              onClick={() => onRunOracle(o.id)}
              disabled={loading}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
      <div className="shrink-0">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">Shortcuts</h2>
        <div className="grid grid-cols-2 gap-1 max-h-[11rem] overflow-y-auto pr-0.5">
          {shortcuts.map((s) => (
            <button
              key={s.id}
              type="button"
              className="play-chip text-left"
              onClick={() => onRunShortcut(s.id)}
              disabled={loading}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="flex items-center gap-2 mb-1.5 shrink-0">
          <button
            type="button"
            className={`text-xs font-semibold uppercase tracking-wider ${logTab === 'lonelog' ? 'text-gray-200' : 'text-muted hover:text-gray-300'}`}
            onClick={() => setLogTab('lonelog')}
          >
            Lonelog
          </button>
          <span className="text-muted text-xs">|</span>
          <button
            type="button"
            className={`text-xs font-semibold uppercase tracking-wider ${logTab === 'audit' ? 'text-gray-200' : 'text-muted hover:text-gray-300'}`}
            onClick={() => setLogTab('audit')}
          >
            Audit
          </button>
        </div>
        <div className="flex-1 min-h-0 rounded-md border border-border bg-bg/40 p-2 overflow-y-auto">
          {logTab === 'lonelog' ? (
            visibleLog.length === 0 ? (
              <p className="text-xs text-muted italic">Session events will appear here.</p>
            ) : (
              <div className="space-y-2">
                {visibleLog.map((line) => (
                  <div
                    key={`log-${line.slice(0, 40)}-${line.length}`}
                    className="text-xs leading-relaxed text-gray-400 border-b border-border/40 pb-2 last:border-0 last:pb-0"
                  >
                    <MarkdownContent content={line} className="text-xs" />
                  </div>
                ))}
              </div>
            )
          ) : visibleAudit.length === 0 ? (
            <p className="text-xs text-muted italic">Mechanical audit events will appear here.</p>
          ) : (
            <div className="space-y-1.5">
              {visibleAudit.map((event, idx) => (
                <div
                  key={`audit-${event.ts ?? idx}-${event.event}-${idx}`}
                  className="text-xs leading-relaxed text-gray-400 border-b border-border/40 pb-1.5 last:border-0 last:pb-0"
                >
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] text-muted tabular-nums">{formatAuditTime(event.ts)}</span>
                    <span className="text-[10px] uppercase tracking-wide text-amber-200/80">
                      {event.event.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={`text-[10px] px-1 py-0 rounded ${isInferredAudit(event) ? 'bg-purple-500/20 text-purple-200' : 'bg-emerald-500/15 text-emerald-200'}`}
                    >
                      {isInferredAudit(event) ? 'inferred' : 'code'}
                    </span>
                    {event.source && <span className="text-[10px] text-muted truncate">{event.source}</span>}
                  </div>
                  <p className="mt-0.5 text-gray-300">{formatAuditSummary(event)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {sources.length > 0 && (
        <div className="shrink-0">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted mb-2">Sources</h2>
          <ul className="text-xs text-muted space-y-1">
            {sources.slice(0, 4).map((s) => (
              <li key={`${s.source_label}-${s.page}`} className="truncate">
                {s.source_label} p.{s.page}
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}

function CombatPanel({ state }: { state: CombatStateSnapshot }) {
  const byId = new Map(state.combatants.map((c) => [c.id, c]));
  return (
    <div className="shrink-0 rounded-lg border border-red-500/30 bg-red-500/5 p-2.5 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-red-300/90">Combat</h2>
        <span className="text-[10px] text-muted">Round {state.round}</span>
      </div>
      <p className="text-sm font-medium text-gray-200 truncate" title={state.encounter_name}>
        {state.encounter_name}
      </p>
      <ol className="space-y-1 max-h-[10rem] overflow-y-auto pr-0.5">
        {state.order.map((id) => {
          const c = byId.get(id);
          if (!c) return null;
          const isCurrent = id === state.current_combatant_id;
          const down = c.hp <= 0;
          return (
            <li
              key={id}
              className={`text-xs rounded px-2 py-1 border ${
                isCurrent ? 'border-accent/50 bg-accent/10 text-gray-100' : 'border-border/50 bg-bg/30 text-gray-400'
              } ${down ? 'opacity-50 line-through' : ''}`}
            >
              <span className="font-medium">{c.name}</span>
              {c.kind === 'enemy' && (
                <span className="text-muted ml-1">
                  HP {c.hp}/{c.max_hp} · AC {c.ac}
                </span>
              )}
              {isCurrent && <span className="ml-1 text-accent text-[10px] uppercase">turn</span>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
