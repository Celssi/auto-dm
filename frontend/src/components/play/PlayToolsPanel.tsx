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
  oracles: { id: string; label: string }[];
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
  if (activeLogTab === 'combat' && brambletrekCombat) {
    return <BrambletrekCombatPanel combat={brambletrekCombat} onAction={onBrambletrekCombatAction} embedded />;
  }
  if (activeLogTab === 'lonelog') return <PlayLonelogView lonelog={lonelog} />;
  if (activeLogTab === 'audit') return <PlayAuditView auditEvents={auditEvents} />;
  return null;
}
