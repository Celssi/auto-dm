import type { Character } from '../../../types';
import { displayLabel, EMPTY_FIELD } from '../../../lib/displayText';
import { CombatStat, SheetSection } from './characterSheetViewParts';
import { formatMod, proficiencyBonus } from './sheetUtils';

interface Props {
  character: Character;
  editable?: boolean;
  onChange?: (patch: Partial<Character>) => void;
}

export default function CharacterSheetHeader({ character: c, editable, onChange }: Props) {
  const pb = proficiencyBonus(c.level || 1);

  const classLine =
    (c.classes?.length ? c.classes : [{ class_name: c.class_name, level: c.level, subclass: c.subclass }])
      .map((e) => `${displayLabel(e.class_name)} ${e.level}${e.subclass ? ` (${displayLabel(e.subclass)})` : ''}`)
      .join(' · ') ||
    displayLabel(c.class_name) ||
    EMPTY_FIELD;

  const patch = (p: Partial<Character>) => onChange?.({ ...c, ...p });

  return (
    <SheetSection className="!p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {editable ? (
            <input
              className="w-full bg-transparent text-2xl font-bold text-accent focus:outline-none border-b border-transparent focus:border-accent/40 pb-1"
              value={c.name || ''}
              onChange={(e) => patch({ name: e.target.value })}
              placeholder="Character name"
              aria-label="Character name"
            />
          ) : (
            <h2 className="text-2xl font-bold text-accent">{c.name || 'Unnamed'}</h2>
          )}
          <p className="text-sm text-muted mt-1">
            {[displayLabel(c.species), classLine, displayLabel(c.background)].filter(Boolean).join(' · ')}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          <CombatStat label="Level" value={String(c.level || 1)} />
          <CombatStat label="Proficiency" value={formatMod(pb)} />
          <CombatStat label="XP" value={String(c.xp || 0)} />
        </div>
      </div>
    </SheetSection>
  );
}
