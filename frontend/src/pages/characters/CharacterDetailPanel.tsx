import { useRef, useState } from 'react';
import { m } from '../../lib/framer';
import type { BrambletrekCharacter, Character } from '../../types';
import type { PdfUnlockedFeatures } from '../../games/dnd5e/character-sheet/characterSheetPdfAssembly';
import CharacterSheetView from '../../games/dnd5e/character-sheet/CharacterSheetView';
import CharacterSheetHeader from '../../games/dnd5e/character-sheet/CharacterSheetHeader';
import CreationChoicesForm from '../../games/dnd5e/character-sheet/CreationChoicesForm';
import MulticlassPanel from '../../games/dnd5e/character-sheet/MulticlassPanel';
import UnlockedFeaturesPanel from '../../games/dnd5e/character-sheet/UnlockedFeaturesPanel';
import { getGameCharacterConfig } from '../../games/registry';
import { GameCharacterSetup } from '../../games/components';
import { brambletrekSummaryLine } from '../../games/brambletrek/sheetUtils';
import { fadeUp } from '../../components/ui/motion';
import OverflowMenu from '../../components/ui/OverflowMenu';

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
  return (
    <m.div variants={fadeUp} className="space-y-5">
      <div className="flex flex-wrap items-center gap-2 panel-glow p-3">
        <button type="button" className="btn-ghost" onClick={onBack}>
          ← Back
        </button>
        <div className="w-px h-6 bg-border hidden sm:block" />
        <button type="button" className="btn-ghost" onClick={onEdit}>
          Edit
        </button>
        <div className="ml-auto">
          <OverflowMenu items={[{ label: 'Delete', onSelect: onDelete, danger: true }]} />
        </div>
      </div>

      <div className="panel-glow p-4">
        <h2 className="display-title text-xl">{bt.name || 'Unnamed Gnawborn'}</h2>
        <p className="text-sm text-muted mt-1">{brambletrekSummaryLine(bt, summary)}</p>
        {typeof summary.reason === 'string' && summary.reason && (
          <p className="text-xs text-muted mt-2">Reason: {summary.reason}</p>
        )}
      </div>

      <GameCharacterSetup
        gameId={gameId}
        characterId={activeId}
        entity={character as Record<string, unknown>}
        onChange={(entity) => onChange(entity as Character)}
        onSaved={(entity) => onSave(entity as Character, { silentToast: true, alreadyPersisted: true })}
      />
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
  const snapshotRef = useRef<Character | null>(null);
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
        onExportPdf={() => {
          void (async () => {
            const { downloadCharacterPdf } = await import('../../games/dnd5e/character-sheet/CharacterSheetPdf');
            const feats = summary?.unlocked_features as PdfUnlockedFeatures | undefined;
            downloadCharacterPdf(character, undefined, feats);
          })();
        }}
        onEditSetup={onEdit}
        onDelete={onDelete}
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

      <CharacterSheetView
        character={character}
        summary={summary}
        editable={editing}
        hideHeader
        onChange={(c) => onChange(c as Character)}
      />
    </m.div>
  );
}

function DndSheetToolbar({
  editing,
  onBack,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onLevelUp,
  onExportPdf,
  onEditSetup,
  onDelete,
}: {
  editing: boolean;
  onBack: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onLevelUp: () => void;
  onExportPdf: () => void;
  onEditSetup: () => void;
  onDelete: () => void;
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
      <button type="button" className="btn-ghost" onClick={onExportPdf}>
        Export PDF
      </button>
      {editing && (
        <button type="button" className="btn-primary ml-auto" onClick={onSaveEdit}>
          Save changes
        </button>
      )}
      <div className={editing ? '' : 'ml-auto'}>
        <OverflowMenu
          items={[
            { label: 'Edit character setup', onSelect: onEditSetup },
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
}: {
  missingChoices: string[];
  choicesOpen: boolean;
  editing: boolean;
  character: Character;
  charOptions: Record<string, unknown>;
  onToggle: () => void;
  onChange: (c: Character) => void;
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
          {editing ? (
            <CreationChoicesForm
              char={character}
              options={charOptions}
              patch={(p) => onChange({ ...character, ...p })}
            />
          ) : (
            <p className="text-xs text-muted">Edit the sheet to complete these choices.</p>
          )}
        </>
      )}
    </div>
  );
}
