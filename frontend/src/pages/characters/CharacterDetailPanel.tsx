import { useRef, useState } from 'react';
import { m } from '../../lib/framer';
import { api } from '../../api/client';
import type { BrambletrekCharacter, Character } from '../../types';
import type { PdfUnlockedFeatures } from '../../games/dnd5e/character-sheet/characterSheetPdfAssembly';
import CharacterSheetView from '../../games/dnd5e/character-sheet/CharacterSheetView';
import CharacterSheetHeader from '../../games/dnd5e/character-sheet/CharacterSheetHeader';
import CreationChoicesForm from '../../games/dnd5e/character-sheet/CreationChoicesForm';
import MulticlassPanel from '../../games/dnd5e/character-sheet/MulticlassPanel';
import UnlockedFeaturesPanel from '../../games/dnd5e/character-sheet/UnlockedFeaturesPanel';
import { getGameCharacterConfig } from '../../games/registry';
import { GameCharacterSetup } from '../../games/components';
import BrambletrekSheetView from '../../games/brambletrek/BrambletrekSheetView';
import { brambletrekSummaryLine } from '../../games/brambletrek/sheetUtils';
import { fadeUp } from '../../components/ui/motion';
import OverflowMenu from '../../components/ui/OverflowMenu';
import { useToast } from '../../components/ui/toast';

type UnlockedFeatures = import('../../games/dnd5e/character-sheet/UnlockedFeaturesPanel').UnlockedFeatures;

type Props = {
  character: Character;
  activeId: string | null;
  summary: Record<string, unknown>;
  charOptions: Record<string, unknown>;
  onBack: () => void;
  onEdit: () => void;
  onLevelUp: () => void;
  onSave: (c: Character, opts?: { silentToast?: boolean; alreadyPersisted?: boolean }) => void | Promise<void>;
  onDelete: () => void;
  onChange: (c: Character) => void;
};

export default function CharacterDetailPanel({
  character,
  activeId,
  summary,
  charOptions,
  onBack,
  onEdit,
  onLevelUp,
  onSave,
  onDelete,
  onChange,
}: Props) {
  const gameId = character.game_id || 'dnd5e';
  if (getGameCharacterConfig(gameId).id === 'brambletrek') {
    return (
      <BrambletrekCharacterDetail
        character={character}
        activeId={activeId}
        summary={summary}
        onBack={onBack}
        onEdit={onEdit}
        onSave={onSave}
        onDelete={onDelete}
        onChange={onChange}
      />
    );
  }
  return (
    <DndCharacterDetail
      character={character}
      activeId={activeId}
      summary={summary}
      charOptions={charOptions}
      onBack={onBack}
      onEdit={onEdit}
      onLevelUp={onLevelUp}
      onSave={onSave}
      onDelete={onDelete}
      onChange={onChange}
    />
  );
}

function BrambletrekCharacterDetail({
  character,
  activeId,
  summary,
  onBack,
  onEdit,
  onSave,
  onDelete,
  onChange,
}: Omit<Props, 'charOptions' | 'onLevelUp'>) {
  const gameId = character.game_id || 'brambletrek';
  const bt = character as unknown as BrambletrekCharacter;
  const [editing, setEditing] = useState(false);
  const snapshotRef = useRef<Character | null>(null);

  const startEdit = () => {
    snapshotRef.current = character;
    setEditing(true);
  };
  const cancelEdit = () => {
    if (snapshotRef.current) onChange(snapshotRef.current);
    snapshotRef.current = null;
    setEditing(false);
  };

  return (
    <m.div variants={fadeUp} className="space-y-5">
      <div className="flex flex-wrap items-center gap-2 panel-glow p-3">
        <button type="button" className="btn-ghost" onClick={onBack}>
          ← Back
        </button>
        <div className="w-px h-6 bg-border hidden sm:block" />
        {editing ? (
          <button type="button" className="btn-ghost" onClick={cancelEdit}>
            Cancel
          </button>
        ) : (
          <button type="button" className="btn-ghost" onClick={startEdit}>
            Edit
          </button>
        )}
        <div className="ml-auto">
          <OverflowMenu
            items={[
              { label: 'Open full editor', onSelect: onEdit },
              { label: 'Delete', onSelect: onDelete, danger: true },
            ]}
          />
        </div>
      </div>

      <div className="panel-glow p-4">
        <h2 className="display-title text-xl">{bt.name || 'Unnamed Gnawborn'}</h2>
        <p className="text-sm text-muted mt-1">{brambletrekSummaryLine(bt, summary)}</p>
        {typeof summary.reason === 'string' && summary.reason && (
          <p className="text-xs text-muted mt-2">Reason: {summary.reason}</p>
        )}
      </div>

      {editing ? (
        <GameCharacterSetup
          gameId={gameId}
          characterId={activeId}
          entity={character as Record<string, unknown>}
          onChange={(entity) => onChange(entity as Character)}
          onSaved={(entity) => {
            snapshotRef.current = null;
            setEditing(false);
            void onSave(entity as Character, { silentToast: true, alreadyPersisted: true });
          }}
        />
      ) : (
        <BrambletrekSheetView character={bt} summary={summary} />
      )}
    </m.div>
  );
}

function DndCharacterDetail({
  character,
  activeId,
  summary,
  charOptions,
  onBack,
  onEdit,
  onLevelUp,
  onSave,
  onDelete,
  onChange,
}: Props) {
  const [choicesOpen, setChoicesOpen] = useState(true);
  const [editing, setEditing] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const snapshotRef = useRef<Character | null>(null);
  const toast = useToast();
  const unlockedFeatures = summary.unlocked_features as UnlockedFeatures | undefined;
  const missingChoices = (summary.missing_creation_choices as string[]) || [];

  const startEdit = () => {
    snapshotRef.current = character;
    setEditing(true);
  };
  const cancelEdit = () => {
    if (snapshotRef.current) onChange(snapshotRef.current);
    snapshotRef.current = null;
    setEditing(false);
  };
  const saveEdit = async () => {
    await onSave(character);
    snapshotRef.current = null;
    setEditing(false);
  };

  return (
    <m.div variants={fadeUp} className="space-y-5">
      <DndSheetToolbar
        editing={editing}
        onBack={onBack}
        onStartEdit={startEdit}
        onCancelEdit={cancelEdit}
        onSaveEdit={() => void saveEdit()}
        onLevelUp={onLevelUp}
        exportingPdf={exportingPdf}
        onExportPdf={() => {
          if (exportingPdf) return;
          void (async () => {
            setExportingPdf(true);
            try {
              const { downloadCharacterPdf } = await import('../../games/dnd5e/character-sheet/CharacterSheetPdf');
              const feats = summary?.unlocked_features as PdfUnlockedFeatures | undefined;
              await downloadCharacterPdf(character, undefined, feats);
            } catch (err) {
              const message = err instanceof Error && err.message ? err.message : 'Could not export PDF.';
              toast.error(message);
            } finally {
              setExportingPdf(false);
            }
          })();
        }}
        onEditSetup={onEdit}
        onDelete={onDelete}
        onRebuild={
          activeId
            ? () => {
                void (async () => {
                  const { character: rebuilt } = await api.rebuildCharacter(activeId);
                  await onSave(rebuilt as Character, { alreadyPersisted: true });
                })();
              }
            : undefined
        }
      />

      {missingChoices.length > 0 && (
        <MissingChoicesPanel
          missingChoices={missingChoices}
          choicesOpen={choicesOpen}
          editing={editing}
          character={character}
          charOptions={charOptions}
          onToggle={() => setChoicesOpen((value) => !value)}
          onChange={onChange}
          onRebuild={
            activeId
              ? () => {
                  void (async () => {
                    const { character: rebuilt } = await api.rebuildCharacter(activeId);
                    await onSave(rebuilt as Character, { alreadyPersisted: true });
                  })();
                }
              : undefined
          }
        />
      )}

      {Boolean(summary.needs_asi) && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
          ASI or feat choice available. Level up or edit to apply.
        </div>
      )}

      <CharacterSheetHeader
        character={character}
        editable={editing}
        onChange={(patch) => onChange({ ...character, ...patch })}
      />

      {unlockedFeatures && <UnlockedFeaturesPanel features={unlockedFeatures} />}

      {editing && (
        <MulticlassPanel
          character={{ ...character, id: activeId || undefined }}
          onChange={(classes) => onChange({ ...character, classes })}
        />
      )}

      {editing && (
        <div className="panel p-4 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">2024 choices</h3>
          <p className="text-xs text-muted">
            Origin feat spells and other picks. Magic Initiate cantrips and the 1st-level spell can be changed here.
          </p>
          <CreationChoicesForm char={character} options={charOptions} patch={(p) => onChange({ ...character, ...p })} />
        </div>
      )}

      <CharacterSheetView
        character={character}
        summary={summary}
        editable={editing}
        hideHeader
        onChange={(c) => onChange(c as Character)}
        onToggleHeroicInspiration={async (next) => {
          onChange({ ...character, heroic_inspiration: next });
          if (activeId && !editing) {
            try {
              const res = await api.patchLiveCharacter(activeId, { heroic_inspiration: next });
              onChange(res.character as Character);
            } catch (err) {
              toast.error(err instanceof Error ? err.message : 'Could not update Heroic Inspiration');
            }
          }
        }}
      />
    </m.div>
  );
}

function DndSheetToolbar({
  editing,
  exportingPdf,
  onBack,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onLevelUp,
  onExportPdf,
  onEditSetup,
  onDelete,
  onRebuild,
}: {
  editing: boolean;
  exportingPdf?: boolean;
  onBack: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onLevelUp: () => void;
  onExportPdf: () => void;
  onEditSetup: () => void;
  onDelete: () => void;
  onRebuild?: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 panel-glow p-3">
      <button type="button" className="btn-ghost" onClick={onBack}>
        ← Back
      </button>
      <div className="w-px h-6 bg-border hidden sm:block" />
      {editing ? (
        <button type="button" className="btn-ghost" onClick={onCancelEdit}>
          Cancel
        </button>
      ) : (
        <button type="button" className="btn-ghost" onClick={onStartEdit}>
          Edit
        </button>
      )}
      <button type="button" className="btn-primary" onClick={onLevelUp}>
        Level up
      </button>
      <button
        type="button"
        className="btn-ghost disabled:opacity-50"
        onClick={onExportPdf}
        disabled={exportingPdf}
        aria-busy={exportingPdf}
      >
        {exportingPdf ? 'Exporting PDF...' : 'Export PDF'}
      </button>
      {onRebuild && (
        <button type="button" className="btn-ghost" onClick={onRebuild}>
          Rebuild sheet
        </button>
      )}
      {editing && (
        <button type="button" className="btn-primary ml-auto" onClick={onSaveEdit}>
          Save changes
        </button>
      )}
      <div className={editing ? '' : 'ml-auto'}>
        <OverflowMenu
          items={[
            { label: 'Edit character setup', onSelect: onEditSetup },
            ...(onRebuild ? [{ label: 'Rebuild sheet from 2024 rules', onSelect: onRebuild }] : []),
            { label: 'Delete', onSelect: onDelete, danger: true },
          ]}
        />
      </div>
    </div>
  );
}

function MissingChoicesPanel({
  missingChoices,
  choicesOpen,
  editing,
  character,
  charOptions,
  onToggle,
  onChange,
  onRebuild,
}: {
  missingChoices: string[];
  choicesOpen: boolean;
  editing: boolean;
  character: Character;
  charOptions: Record<string, unknown>;
  onToggle: () => void;
  onChange: (c: Character) => void;
  onRebuild?: () => void;
}) {
  return (
    <div className="panel p-4 space-y-3">
      <button type="button" className="flex w-full items-center justify-between text-left" onClick={onToggle}>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-300">Complete character choices</h3>
        <span className="text-xs text-muted">{choicesOpen ? 'Hide' : 'Show'}</span>
      </button>
      {choicesOpen && (
        <>
          <p className="text-xs text-muted">Still needed: {missingChoices.join('; ')}</p>
          {onRebuild && (
            <button type="button" className="btn-ghost text-xs" onClick={onRebuild}>
              Rebuild sheet
            </button>
          )}
          {editing ? (
            <CreationChoicesForm
              char={character}
              options={charOptions}
              patch={(p) => onChange({ ...character, ...p })}
            />
          ) : (
            <p className="text-xs text-muted">
              Edit the sheet to complete remaining picks. Rebuild sheet keeps HP, slots, and choices already made.
            </p>
          )}
        </>
      )}
    </div>
  );
}
