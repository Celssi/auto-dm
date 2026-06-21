import { useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { api } from '../../../api/client';
import type { Character, ClassLevel } from '../../../types';
import { Field } from '../../../components/ui/forms/Field';
import TextInput from '../../../components/ui/forms/TextInput';
import ChoiceGroup from '../../../components/ui/forms/ChoiceGroup';
import { displayLabel } from '../../../lib/displayText';

interface Props {
  character: Character;
  onChange: (classes: ClassLevel[]) => void;
}

export default function MulticlassPanel({ character, onChange }: Props) {
  const [options, setOptions] = useState<{ id: string; label: string }[]>([]);
  const [addClass, setAddClass] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);

  const entries = (
    character.classes?.length
      ? character.classes
      : character.class_name
        ? [
            {
              class_name: character.class_name,
              level: character.level,
              subclass: character.subclass || '',
            },
          ]
        : []
  ) as ClassLevel[];

  useEffect(() => {
    api.getCharacterOptions(character.campaign_setting === 'faerun').then((o) => {
      setOptions((o.classes as { id: string; label: string }[]) || []);
    });
  }, [character.campaign_setting]);

  const existing = new Set(entries.map((e) => e.class_name));
  const available = options.filter((c) => !existing.has(c.id));
  const canAddClass = character.level < 20 && available.length > 0;
  const sectionTitle = entries.length > 1 ? 'Classes' : 'Class';

  const updateEntry = (idx: number, patch: Partial<ClassLevel>) => {
    const next = entries.map((e, i) => (i === idx ? { ...e, ...patch } : e));
    onChange(next);
  };

  const tryAdd = async () => {
    if (!addClass) return;
    setError(null);
    try {
      if (character.id) {
        const res = await api.addMulticlass(String(character.id), addClass);
        onChange((res.character.classes as ClassLevel[]) || []);
      } else {
        onChange([...entries, { class_name: addClass, level: 1, subclass: '', class_skill_choices: [] }]);
      }
      setAddClass('');
      setAddOpen(false);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="panel-glow p-4 space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-accent">{sectionTitle}</h3>

      {entries.length === 0 && <p className="text-sm text-muted">Set a primary class first.</p>}
      {entries.map((e, i) => (
        <div
          key={`${e.class_name}-${i}`}
          className="grid grid-cols-[1fr_auto_1fr] gap-3 items-center rounded-lg border border-border bg-bg/30 px-3 py-2 text-sm"
        >
          <span className="font-medium">{displayLabel(e.class_name)}</span>
          <span className="text-accent tabular-nums">Lv {e.level}</span>
          <TextInput
            inputClassName="text-xs py-1.5"
            placeholder="Subclass"
            value={e.subclass || ''}
            onChange={(ev) => updateEntry(i, { subclass: ev.target.value })}
          />
        </div>
      ))}

      {canAddClass && (
        <>
          <button
            type="button"
            className="flex w-full items-center justify-between gap-3 text-left pt-1 cursor-pointer"
            onClick={() => setAddOpen((v) => !v)}
            aria-expanded={addOpen}
            aria-label={addOpen ? 'Hide add class options' : 'Show add class options'}
          >
            <span className="text-xs text-muted">Add another class</span>
            <ChevronDown
              className={`h-4 w-4 text-muted shrink-0 transition-transform duration-200 ${addOpen ? 'rotate-180' : ''}`}
              aria-hidden
            />
          </button>
          {addOpen && (
            <div className="space-y-3 pt-1 border-t border-border/60">
              <Field label="Add class (level 1)">
                <ChoiceGroup
                  value={addClass}
                  onChange={setAddClass}
                  options={available.map((c) => ({ value: c.id, label: c.label }))}
                  allowEmpty
                  columns={2}
                />
                <button type="button" className="btn-primary text-xs mt-2" disabled={!addClass} onClick={tryAdd}>
                  Add class
                </button>
              </Field>
              {error && <p className="text-xs text-danger">{error}</p>}
              <p className="text-[10px] text-muted leading-relaxed">
                Multiclass requires ability score prerequisites (e.g. WIZ INT 13). Level up picks which class gains a
                level.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
