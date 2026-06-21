import { useState } from 'react';
import { m } from '../../lib/framer';
import type { Character } from '../../types';
import type { PdfUnlockedFeatures } from '../../components/character-sheet/characterSheetPdfAssembly';
import CharacterSheetView from '../../components/character-sheet/CharacterSheetView';
import CharacterSheetHeader from '../../components/character-sheet/CharacterSheetHeader';
import CreationChoicesForm from '../../components/character-sheet/CreationChoicesForm';
import MulticlassPanel from '../../components/character-sheet/MulticlassPanel';
import UnlockedFeaturesPanel from '../../components/character-sheet/UnlockedFeaturesPanel';
import { fadeUp } from '../../components/ui/motion';

type UnlockedFeatures = import('../../components/character-sheet/UnlockedFeaturesPanel').UnlockedFeatures;

type Props = {
  character: Character;
  activeId: string | null;
  summary: Record<string, unknown>;
  charOptions: Record<string, unknown>;
  onBack: () => void;
  onEdit: () => void;
  onLevelUp: () => void;
  onSave: (c: Character) => void;
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
  const [choicesOpen, setChoicesOpen] = useState(true);

  const unlockedFeatures = summary.unlocked_features as UnlockedFeatures | undefined;
  const missingChoices = (summary.missing_creation_choices as string[]) || [];

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
        <button type="button" className="btn-primary" onClick={onLevelUp}>
          Level up
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={async () => {
            const { downloadCharacterPdf } = await import('../../components/character-sheet/CharacterSheetPdf');
            const feats = summary?.unlocked_features as PdfUnlockedFeatures | undefined;
            downloadCharacterPdf(character, undefined, feats);
          }}
        >
          Export PDF
        </button>
        <button type="button" className="btn-primary ml-auto" onClick={() => onSave(character)}>
          Save changes
        </button>
        <button type="button" className="btn-danger" onClick={onDelete}>
          Delete
        </button>
      </div>

      {missingChoices.length > 0 && (
        <div className="panel p-4 space-y-3">
          <button
            type="button"
            className="flex w-full items-center justify-between text-left"
            onClick={() => setChoicesOpen((v) => !v)}
          >
            <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-300">
              Complete character choices
            </h3>
            <span className="text-xs text-muted">{choicesOpen ? 'Hide' : 'Show'}</span>
          </button>
          {choicesOpen && (
            <>
              <p className="text-xs text-muted">Still needed: {missingChoices.join('; ')}</p>
              <CreationChoicesForm
                char={character}
                options={charOptions}
                patch={(p) => onChange({ ...character, ...p })}
              />
            </>
          )}
        </div>
      )}

      {Boolean(summary.needs_asi) && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
          ASI or feat choice available. Level up or edit to apply.
        </div>
      )}

      <CharacterSheetHeader character={character} editable onChange={(patch) => onChange({ ...character, ...patch })} />

      {unlockedFeatures && <UnlockedFeaturesPanel features={unlockedFeatures} />}

      <MulticlassPanel
        character={{ ...character, id: activeId || undefined }}
        onChange={(classes) => onChange({ ...character, classes })}
      />

      <CharacterSheetView
        character={character}
        summary={summary}
        editable
        hideHeader
        onChange={(c) => onChange(c as Character)}
      />
    </m.div>
  );
}
