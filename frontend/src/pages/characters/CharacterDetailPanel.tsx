import { useState } from 'react';
import { m } from '../../lib/framer';
import type { Character } from '../../types';
import type { PdfUnlockedFeatures } from '../../components/character-sheet/characterSheetPdfAssembly';
import CharacterSheetView from '../../components/character-sheet/CharacterSheetView';
import CreationChoicesForm from '../../components/character-sheet/CreationChoicesForm';
import MulticlassPanel from '../../components/character-sheet/MulticlassPanel';
import { displayLabel } from '../../lib/displayText';
import GlossaryTip from '../../components/ui/GlossaryTip';
import { fadeUp } from '../../components/ui/motion';

type UnlockedFeatures = {
  class_features?: Record<string, string[]>;
  subclass_features?: Record<string, string[]>;
  species_traits?: Array<{
    id: string;
    label: string;
    detail?: string;
    display: string;
    automatic?: boolean;
  }>;
  origin_feat_effects?: Array<{ feat_id: string; feat: string; effect: string }>;
  resolved_choices?: Array<{ id: string; label: string; value_label: string }>;
};

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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MulticlassPanel
          character={{ ...character, id: activeId || undefined }}
          onChange={(classes) => onChange({ ...character, classes })}
        />
        {unlockedFeatures && (
          <div className="panel p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-accent mb-3">Unlocked features</h3>
            <div className="space-y-2 text-sm">
              {(unlockedFeatures.species_traits || []).length > 0 && (
                <div>
                  <span className="text-muted">Species traits</span>
                  <ul className="mt-1 space-y-1">
                    {(unlockedFeatures.species_traits || []).map((row) => (
                      <li key={row.id} className="text-gray-200">
                        {row.display}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(unlockedFeatures.origin_feat_effects || []).length > 0 && (
                <div>
                  <span className="text-muted">Origin feat effects</span>
                  <ul className="mt-1 space-y-1">
                    {(unlockedFeatures.origin_feat_effects || []).map((row) => (
                      <li key={`${row.feat_id}-${row.effect}`} className="text-gray-200">
                        <GlossaryTip name={row.feat} variant="inline" />: {row.effect}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {Object.entries(unlockedFeatures.class_features || {}).map(([cid, feats]) => (
                <div key={cid}>
                  <span className="text-muted">{displayLabel(cid)}</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {(feats as string[]).map((f) => (
                      <GlossaryTip key={f} name={f} />
                    ))}
                  </div>
                </div>
              ))}
              {Object.entries(unlockedFeatures.subclass_features || {}).map(([key, feats]) => (
                <div key={key}>
                  <span className="text-muted">{displayLabel(key)}</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {(feats as string[]).map((f) => (
                      <GlossaryTip key={f} name={f} />
                    ))}
                  </div>
                </div>
              ))}
              {(unlockedFeatures.resolved_choices || []).map((row) => (
                <div key={row.id}>
                  <span className="text-muted">{row.label}</span>
                  <p className="text-sm mt-0.5">{row.value_label}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <CharacterSheetView character={character} summary={summary} editable onChange={(c) => onChange(c as Character)} />
    </m.div>
  );
}
