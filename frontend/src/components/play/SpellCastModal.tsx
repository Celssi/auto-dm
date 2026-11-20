import { useMemo } from 'react';
import { m } from '../../lib/framer';
import { displayLabel } from '../../lib/displayText';
import type { Character } from '../../types';
import type { SpellCastModalState } from '../../pages/play/playState';

interface SpellOption {
  name: string;
  kind: 'cantrip' | 'prepared' | 'known' | 'spellbook' | 'magic-initiate';
  cantrip: boolean;
  magicInitiate: boolean;
}

interface Props {
  modal: SpellCastModalState;
  character: Character;
  onUpdate: (patch: Partial<SpellCastModalState>) => void;
  onSubmit: () => void;
  onClose: () => void;
}

function norm(name: string) {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '');
}

export function listCastableSpells(character: Character): SpellOption[] {
  const seen = new Set<string>();
  const out: SpellOption[] = [];
  const add = (raw: string, kind: SpellOption['kind'], cantrip: boolean, magicInitiate: boolean) => {
    const name = String(raw || '').trim();
    const key = norm(name);
    if (!name || !key || seen.has(key)) return;
    seen.add(key);
    out.push({ name, kind, cantrip, magicInitiate });
  };
  for (const name of character.cantrips || []) add(name, 'cantrip', true, false);
  for (const name of character.prepared_spells || []) add(name, 'prepared', false, false);
  for (const name of character.known_spells || []) add(name, 'known', false, false);
  for (const name of character.spellbook || []) add(name, 'spellbook', false, false);
  const fc = character.feature_choices || {};
  const miCantrips = fc.magic_initiate_cantrips;
  if (Array.isArray(miCantrips)) {
    for (const name of miCantrips) add(String(name), 'magic-initiate', true, true);
  }
  const miSpell = String(fc.magic_initiate_level1 || '').trim();
  if (miSpell) add(miSpell, 'magic-initiate', false, true);
  return out;
}

function originHasMagicInitiate(character: Character): boolean {
  const feat = `${character.origin_feat || ''} ${character.versatile_origin_feat || ''}`.toLowerCase();
  return feat.includes('magic initiate');
}

export default function SpellCastModal({ modal, character, onUpdate, onSubmit, onClose }: Props) {
  const spells = useMemo(() => listCastableSpells(character), [character]);
  const selected = spells.find((row) => norm(row.name) === norm(modal.spellName)) || spells[0];
  const slotKeys = Object.keys(character.spell_slots || {})
    .map((k) => Number(k))
    .filter((n) => n >= 1)
    .toSorted((a, b) => a - b);
  const remaining = (lvl: number) => Number(character.spell_slots?.[String(lvl)] ?? 0);
  const miUsed = Boolean(character.feature_choices?._magic_initiate_free_used);
  const miSpell = String(character.feature_choices?.magic_initiate_level1 || '').trim();
  const showFree = Boolean(
    selected &&
      !selected.cantrip &&
      originHasMagicInitiate(character) &&
      !miUsed &&
      miSpell &&
      norm(selected.name) === norm(miSpell),
  );

  return (
    <m.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <m.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        className="panel-glow w-full max-w-md p-5 space-y-4"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="spell-modal-title"
      >
        <h2 id="spell-modal-title" className="display-title text-lg">
          Cast spell
        </h2>
        {spells.length === 0 ? (
          <p className="text-sm text-muted">No prepared, known, or Magic Initiate spells on this sheet.</p>
        ) : (
          <>
            <div className="space-y-1">
              <p className="text-xs text-muted uppercase tracking-wider">Spell</p>
              <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
                {spells.map((row) => (
                  <button
                    key={row.name}
                    type="button"
                    onClick={() =>
                      onUpdate({
                        spellName: row.name,
                        slotLevel: row.cantrip ? 0 : Math.max(1, modal.slotLevel || 1),
                        freeUse: row.magicInitiate && showFree,
                      })
                    }
                    className={`w-full text-left px-3 py-2 rounded-md text-sm border ${
                      selected && norm(selected.name) === norm(row.name)
                        ? 'bg-accent/15 text-accent border-accent/25'
                        : 'border-border text-gray-200 hover:border-accent/40'
                    }`}
                  >
                    {displayLabel(row.name)}
                    <span className="block text-[10px] uppercase tracking-wide text-muted">
                      {row.kind.replace('-', ' ')}
                    </span>
                  </button>
                ))}
              </div>
            </div>
            {selected && !selected.cantrip && slotKeys.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-muted uppercase tracking-wider">Slot level</p>
                <div className="flex flex-wrap gap-1.5">
                  {slotKeys.map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => onUpdate({ slotLevel: lvl, freeUse: false })}
                      className={`px-2.5 py-1 rounded-md text-sm border ${
                        modal.slotLevel === lvl && !modal.freeUse
                          ? 'bg-accent/15 text-accent border-accent/25'
                          : 'border-border text-gray-200'
                      }`}
                    >
                      L{lvl} ({remaining(lvl)} left)
                    </button>
                  ))}
                </div>
              </div>
            )}
            {showFree && selected && !selected.cantrip && (
              <label className="flex items-start gap-2 text-sm text-gray-200">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={modal.freeUse}
                  onChange={(e) => onUpdate({ freeUse: e.target.checked })}
                />
                <span>Magic Initiate free cast (once per long rest, no slot)</span>
              </label>
            )}
          </>
        )}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-ghost text-sm" onClick={onClose} disabled={modal.submitting}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary text-sm"
            onClick={onSubmit}
            disabled={modal.submitting || !selected}
          >
            {modal.submitting ? 'Casting…' : `Cast ${displayLabel(selected?.name || 'spell')}`}
          </button>
        </div>
      </m.div>
    </m.div>
  );
}
