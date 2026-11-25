import { useEffect, useState } from 'react';
import { api } from '../../api/client';
import type { AuditEvent, CombatStateSnapshot, Shortcut, Source } from '../../api/client';
import type { DragonkeepState, PendingJourney, BrambletrekCombatState } from '../../types';
import { getGamePlayConfig } from '../../games/play/registry';
import JourneyPanel from '../../games/brambletrek/JourneyPanel';
import DragonkeepPanel from '../../games/brambletrek/DragonkeepPanel';
import DeckPanel from '../../games/brambletrek/DeckPanel';
import BrambletrekCombatPanel from '../../games/brambletrek/CombatPanel';
import CombatPanel from './CombatPanel';
import PlayAuditView from './PlayAuditView';
import PlayLogTabs, { type PlayLogTab } from './PlayLogTabs';
import PlayLonelogView from './PlayLonelogView';
import PlayOracleGrid from './PlayOracleGrid';
import PlayShortcutGrid from './PlayShortcutGrid';
import PlaySourcesList from './PlaySourcesList';
import PlayToolsShell from './PlayToolsShell';

const BASE_LOG_TABS: PlayLogTab[] = ['lonelog', 'audit'];

interface Props {
  gameId: string;
  sessionId: string;
  characterId: string;
  pendingJourney: PendingJourney | null;
  dragonkeep: DragonkeepState | null;
  activeAdventure: string;
  oracles: { id: string; label: string; help?: string }[];
  shortcuts: Shortcut[];
  lonelog: string[];
  auditEvents: AuditEvent[];
  sources: Source[];
  loading: boolean;
  combatState: CombatStateSnapshot | null;
  brambletrekCombat: BrambletrekCombatState | null;
  onRunOracle: (id: string) => void;
  onRunShortcut: (id: string) => void;
  onJourneyApply: (index: number) => Promise<{ summary?: string; item_error?: string | null }>;
  onJourneyDrawItem: (index: number) => Promise<{ item_error?: string | null }>;
  onJourneyFinish: () => Promise<void>;
  onJourneyDiscard: () => Promise<void>;
  onJourneyStartCombat: (index: number) => Promise<void>;
  onDragonkeepAction: (action: string) => Promise<void>;
  onDragonkeepInit: () => Promise<void>;
  onBrambletrekCombatAction: (action: string, handIndex?: number) => Promise<void>;
  onCombatAction: (action: string, targetId?: string) => Promise<void>;
  sheetReady?: boolean;
}

export default function PlayToolsPanel({
  gameId,
  sessionId: _sessionId,
  characterId,
  pendingJourney,
  dragonkeep,
  activeAdventure,
  oracles,
  shortcuts,
  lonelog,
  auditEvents,
  sources,
  loading,
  combatState,
  brambletrekCombat,
  onRunOracle,
  onRunShortcut,
  onJourneyApply,
  onJourneyDrawItem,
  onJourneyFinish,
  onJourneyDiscard,
  onJourneyStartCombat,
  onDragonkeepAction,
  onDragonkeepInit,
  onBrambletrekCombatAction,
  onCombatAction,
  sheetReady = true,
}: Props) {
  const config = getGamePlayConfig(gameId);
  const toolTabs: PlayLogTab[] = [...config.extraToolTabs];
  if (activeAdventure === 'dragonkeep') {
    toolTabs.unshift('dragonkeep');
  }
  if (brambletrekCombat?.status === 'active') {
    if (!toolTabs.includes('combat')) {
      toolTabs.unshift('combat');
    }
  }
  const tabs: PlayLogTab[] = [...toolTabs, ...BASE_LOG_TABS];
  const [logTab, setLogTab] = useState<PlayLogTab>(toolTabs[0] ?? 'lonelog');
  const combatForced = brambletrekCombat?.status === 'active' && tabs.includes('combat');
  const activeLogTab = combatForced ? 'combat' : logTab;
  const [deckRemaining, setDeckRemaining] = useState(52);
  const journeyKey = pendingJourney?.events?.map((e) => e.card).join('|') ?? '';

  // New journey draws: open the Journey tab so Apply / Finish day are right there.
  useEffect(() => {
    if (journeyKey && tabs.includes('journey')) setLogTab('journey');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [journeyKey]);
  const [shortcutLoading, setShortcutLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!config.extraToolTabs.includes('deck') || !characterId) return;
    api
      .brambletrekDeckStatus(characterId)
      .then((r) => setDeckRemaining(r.remaining))
      .catch(() => {});
  }, [config.extraToolTabs, characterId, pendingJourney]);

  const runShortcut = async (id: string) => {
    if (config.shortcutGroups) {
      setShortcutLoading(id);
      try {
        await onRunShortcut(id);
      } finally {
        setShortcutLoading(null);
      }
      return;
    }
    onRunShortcut(id);
  };

  const refreshDeck = () => {
    if (!characterId) return;
    api
      .brambletrekDeckStatus(characterId)
      .then((r) => setDeckRemaining(r.remaining))
      .catch(() => {});
  };

  return (
    <PlayToolsShell>
      {config.usesCombatPanel && combatState?.status === 'active' && (
        <CombatPanel state={combatState} onAction={onCombatAction} />
      )}
      {config.usesOracles && <PlayOracleGrid oracles={oracles} loading={loading} onRun={onRunOracle} />}
      <PlayShortcutGrid
        shortcuts={shortcuts}
        loading={loading}
        onRun={runShortcut}
        grouped={config.shortcutGroups}
        shortcutLoading={shortcutLoading}
        sheetReady={sheetReady}
      />
      <PlayLogTabs tabs={tabs} active={activeLogTab} onChange={setLogTab}>
        <PlayToolTabContent
          activeLogTab={activeLogTab}
          dragonkeep={dragonkeep}
          pendingJourney={pendingJourney}
          characterId={characterId}
          deckRemaining={deckRemaining}
          brambletrekCombat={brambletrekCombat}
          lonelog={lonelog}
          auditEvents={auditEvents}
          onDragonkeepAction={onDragonkeepAction}
          onDragonkeepInit={onDragonkeepInit}
          onJourneyApply={onJourneyApply}
          onJourneyDrawItem={onJourneyDrawItem}
          onJourneyFinish={onJourneyFinish}
          onJourneyDiscard={onJourneyDiscard}
          onJourneyStartCombat={onJourneyStartCombat}
          onRefreshDeck={refreshDeck}
          onBrambletrekCombatAction={onBrambletrekCombatAction}
        />
      </PlayLogTabs>
      <PlaySourcesList sources={sources} />
    </PlayToolsShell>
  );
}

function PlayToolTabContent({
  activeLogTab,
  dragonkeep,
  pendingJourney,
  characterId,
  deckRemaining,
  brambletrekCombat,
  lonelog,
  auditEvents,
  onDragonkeepAction,
  onDragonkeepInit,
  onJourneyApply,
  onJourneyDrawItem,
  onJourneyFinish,
  onJourneyDiscard,
  onJourneyStartCombat,
  onRefreshDeck,
  onBrambletrekCombatAction,
}: {
  activeLogTab: PlayLogTab;
  dragonkeep: DragonkeepState | null;
  pendingJourney: PendingJourney | null;
  characterId: string;
  deckRemaining: number;
  brambletrekCombat: BrambletrekCombatState | null;
  lonelog: string[];
  auditEvents: AuditEvent[];
  onDragonkeepAction: (action: string) => Promise<void>;
  onDragonkeepInit: () => Promise<void>;
  onJourneyApply: (index: number) => Promise<{ summary?: string; item_error?: string | null }>;
  onJourneyDrawItem: (index: number) => Promise<{ item_error?: string | null }>;
  onJourneyFinish: () => Promise<void>;
  onJourneyDiscard: () => Promise<void>;
  onJourneyStartCombat: (index: number) => Promise<void>;
  onRefreshDeck: () => void;
  onBrambletrekCombatAction: (action: string, handIndex?: number) => Promise<void>;
}) {
  if (activeLogTab === 'dragonkeep') {
    return <DragonkeepPanel state={dragonkeep} onAction={onDragonkeepAction} onInit={onDragonkeepInit} embedded />;
  }
  if (activeLogTab === 'journey') {
    return (
      <JourneyPanel
        journey={pendingJourney}
        onApply={onJourneyApply}
        onDrawItem={onJourneyDrawItem}
        onFinish={onJourneyFinish}
        onDiscard={onJourneyDiscard}
        onStartCombat={onJourneyStartCombat}
        embedded
      />
    );
  }
  if (activeLogTab === 'deck' && characterId) {
    return <DeckPanel characterId={characterId} remaining={deckRemaining} onAction={onRefreshDeck} embedded />;
  }
  if (activeLogTab === 'combat') {
    const active = brambletrekCombat?.status === 'active';
    return (
      <div>
        {brambletrekCombat && (
          <BrambletrekCombatPanel combat={brambletrekCombat} onAction={onBrambletrekCombatAction} embedded />
        )}
        {!active && <ManualCombatStart onStart={(rank, suit) => onBrambletrekCombatAction(`start:${rank}:${suit}`)} />}
      </div>
    );
  }
  if (activeLogTab === 'lonelog') return <PlayLonelogView lonelog={lonelog} />;
  if (activeLogTab === 'audit') return <PlayAuditView auditEvents={auditEvents} />;
  return null;
}

const COMBAT_RANKS = [
  { id: 'jack', label: 'Jack (10 Health)' },
  { id: 'queen', label: 'Queen (12 Health)' },
  { id: 'king', label: 'King (14 Health)' },
];
const COMBAT_SUITS = ['hearts', 'diamonds', 'spades', 'clubs'];

function ManualCombatStart({ onStart }: { onStart: (rank: string, suit: string) => Promise<void> }) {
  const [rank, setRank] = useState('jack');
  const [suit, setSuit] = useState('clubs');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return (
    <div className="mt-3 rounded-xl border border-border bg-bg/40 p-3">
      <div className="section-heading mb-2">Start combat</div>
      <p className="text-[11px] text-muted mb-2 leading-relaxed">
        Face cards mean combat. Journey face cards have their own Start combat button; use this for a physical-deck draw
        or a narrated encounter. Hearts/Diamonds are the red table (item on victory).
      </p>
      <div className="flex gap-2 mb-2">
        <select
          className="input flex-1 text-xs"
          value={rank}
          onChange={(e) => setRank(e.target.value)}
          aria-label="Opponent card"
        >
          {COMBAT_RANKS.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
        <select
          className="input flex-1 text-xs"
          value={suit}
          onChange={(e) => setSuit(e.target.value)}
          aria-label="Suit"
        >
          {COMBAT_SUITS.map((s) => (
            <option key={s} value={s}>
              {s[0].toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
      </div>
      <button
        type="button"
        className="btn-primary w-full text-xs"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError('');
          try {
            await onStart(rank, suit);
          } catch (e) {
            setError(e instanceof Error ? e.message : 'Could not start combat');
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? 'Starting…' : 'Start combat'}
      </button>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
    </div>
  );
}
