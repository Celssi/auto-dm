import type { ReactNode } from 'react';
import { displayLabel, EMPTY_FIELD } from '../../lib/displayText';
import { GlossaryTagList } from '../ui/GlossaryTip';
import MarkdownContent from '../ui/MarkdownContent';
import { formatAbilityMod } from './sheetUtils';

export function SheetSection({
  title,
  children,
  className = '',
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`sheet-section ${className}`}>
      {title && <h3 className="sheet-heading shrink-0">{title}</h3>}
      {children}
    </section>
  );
}

export function SheetField({
  label,
  value,
  editable,
  onChange,
  className = '',
  mono,
  multiline,
  fill,
  hideLabel,
  plain,
}: {
  label: string;
  value: string;
  editable?: boolean;
  onChange?: (v: string) => void;
  className?: string;
  mono?: boolean;
  multiline?: boolean;
  fill?: boolean;
  hideLabel?: boolean;
  plain?: boolean;
}) {
  const wrapperClass = plain
    ? `flex flex-col min-h-0 ${fill ? 'flex-1' : ''} ${className}`.trim()
    : `sheet-field ${fill ? 'flex flex-col flex-1 min-h-0' : ''} ${className}`.trim();
  const textareaClass =
    `sheet-value-textarea ${fill ? 'sheet-value-textarea-tall' : ''} ${mono ? 'font-mono' : ''}`.trim();
  const multilineClass =
    `sheet-value-multiline ${fill ? 'sheet-value-multiline-tall' : ''} ${mono ? 'font-mono' : ''}`.trim();

  return (
    <div className={wrapperClass}>
      {!hideLabel && label ? <div className="sheet-label shrink-0">{label}</div> : null}
      {editable && onChange ? (
        multiline ? (
          <textarea
            className={textareaClass}
            value={value}
            rows={fill ? undefined : 6}
            onChange={(e) => onChange(e.target.value)}
            aria-label={label || 'Field'}
          />
        ) : (
          <input
            className={`sheet-value-input ${mono ? 'font-mono' : ''}`}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            aria-label={label || 'Field'}
          />
        )
      ) : multiline ? (
        value ? (
          <div className={multilineClass}>
            <MarkdownContent content={value} />
          </div>
        ) : (
          <div className={multilineClass}>{EMPTY_FIELD}</div>
        )
      ) : (
        <div className={`sheet-value ${mono ? 'font-mono' : ''}`}>{value ? displayLabel(value) : EMPTY_FIELD}</div>
      )}
    </div>
  );
}

export function CombatStat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`sheet-combat-stat ${accent ? 'sheet-combat-stat-accent' : ''}`}>
      <div className="sheet-label">{label}</div>
      <div className="text-xl font-bold text-gray-100">{value}</div>
    </div>
  );
}

export function AbilityTile({
  ab,
  score,
  save,
  proficient,
}: {
  ab: string;
  score: number;
  save: string;
  proficient: boolean;
}) {
  return (
    <div className="sheet-ability">
      <span className="sheet-label">{ab}</span>
      <span className="text-2xl font-bold text-accent leading-none">{score}</span>
      <span className="text-sm text-gray-300">{formatAbilityMod(score)}</span>
      <span className="text-[10px] text-muted mt-1">Save {save}</span>
      {proficient && <span className="text-[9px] text-accent/80 mt-0.5">● save</span>}
    </div>
  );
}
export function SpellSlotPips({ level, remaining, max }: { level: string; remaining: number; max: number }) {
  if (max <= 0) return null;
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted w-7 shrink-0">L{level}</span>
      <div className="flex flex-wrap gap-1">
        {Array.from({ length: max }).map((_, i) => (
          <span
            key={i}
            className={`w-3 h-3 rounded-full border transition-colors ${
              i < remaining
                ? 'bg-accent/90 border-accent shadow-[0_0_6px_rgba(201,162,39,0.4)]'
                : 'border-border bg-bg/80'
            }`}
          />
        ))}
      </div>
      <span className="text-xs text-muted tabular-nums">
        {remaining}/{max}
      </span>
    </div>
  );
}

export function ResourcePips({ label, remaining, max }: { label: string; remaining: number; max: number }) {
  if (max <= 0) return null;
  return (
    <div className="space-y-1">
      <div className="sheet-label">{label}</div>
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          {Array.from({ length: max }).map((_, i) => (
            <span
              key={i}
              className={`w-3 h-3 rounded-sm border ${
                i < remaining ? 'bg-emerald-500/80 border-emerald-400/60' : 'border-border bg-bg/80'
              }`}
            />
          ))}
        </div>
        <span className="text-xs text-gray-300">
          {remaining}/{max} remaining
        </span>
      </div>
    </div>
  );
}

export function TagList({ items, classId }: { items: string[]; classId?: string }) {
  return <GlossaryTagList items={items} classId={classId} />;
}

export function DeathSaves({ successes, failures }: { successes: number; failures: number }) {
  return (
    <div className="sheet-field">
      <div className="sheet-label">Death Saves</div>
      <div className="flex gap-4 mt-1">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-muted uppercase">Success</span>
          {[0, 1, 2].map((i) => (
            <span key={i} className={`text-base ${i < successes ? 'text-emerald-400' : 'text-border'}`}>
              {i < successes ? '●' : '○'}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-muted uppercase">Failure</span>
          {[0, 1, 2].map((i) => (
            <span key={i} className={`text-base ${i < failures ? 'text-red-400' : 'text-border'}`}>
              {i < failures ? '●' : '○'}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function HpBar({ hp, maxHp }: { hp: number; maxHp: number }) {
  const pct = maxHp ? Math.min(100, Math.round((hp / maxHp) * 100)) : 0;
  const color = pct > 50 ? 'bg-emerald-500' : pct > 25 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="mt-2">
      <div className="h-2 rounded-full bg-bg border border-border overflow-hidden">
        <div className={`h-full ${color} transition-all duration-300`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
