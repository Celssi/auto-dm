import { useCallback } from 'react';
import { m } from '../../lib/framer';
import type { DiceModalState, Advantage } from '../../pages/play/playState';
import SegmentedControl from '../ui/forms/SegmentedControl';
import DiceRollManualSection from './DiceRollManualSection';
import DiceRollAutoSection from './DiceRollAutoSection';

const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const;

const ADVANTAGE_OPTIONS = [
  { value: 'normal', label: 'Normal' },
  { value: 'advantage', label: 'Advantage' },
  { value: 'disadvantage', label: 'Disadvantage' },
];

const MODE_OPTIONS = [
  { value: 'manual', label: 'Roll manually' },
  { value: 'auto', label: 'Auto-roll' },
];

interface Props {
  modal: DiceModalState;
  abilityScores: Record<string, number>;
  saveProficiencies: string[];
  level: number;
  onUpdate: (patch: Partial<DiceModalState>) => void;
  onSubmit: (preRolled?: number[]) => void;
  onClose: () => void;
}

function computeModifier(ability: string, scores: Record<string, number>, proficient: boolean, level: number): number {
  const score = scores[ability.toLowerCase()] ?? 10;
  let mod = Math.floor((score - 10) / 2);
  if (proficient) mod += 2 + Math.floor((Math.max(1, level) - 1) / 4);
  return mod;
}

export default function DiceRollModal({
  modal,
  abilityScores,
  saveProficiencies,
  level,
  onUpdate,
  onSubmit,
  onClose,
}: Props) {
  const {
    shortcutId,
    label,
    ability,
    advantage,
    proficient,
    modifier,
    diceCount,
    hasModifier,
    showAbilityPicker,
    showProficiency,
    mode,
    manualValues,
    autoResult,
    rolling,
    submitting,
  } = modal;

  const handleAbilityChange = useCallback(
    (ab: string) => {
      const isProfSave = saveProficiencies.includes(ab.toLowerCase());
      const prof = shortcutId === 'saving_throw' ? isProfSave : proficient;
      const mod = computeModifier(ab, abilityScores, prof, level);
      onUpdate({ ability: ab, modifier: mod, proficient: prof });
    },
    [abilityScores, level, proficient, saveProficiencies, shortcutId, onUpdate],
  );

  const handleAdvantageChange = useCallback(
    (adv: string) => {
      const newCount = adv === 'normal' ? 1 : 2;
      onUpdate({
        advantage: adv as Advantage,
        diceCount: newCount,
        manualValues: Array(newCount).fill(null),
        autoResult: null,
      });
    },
    [onUpdate],
  );

  const handleProficiencyToggle = useCallback(() => {
    const newProf = !proficient;
    const mod = computeModifier(ability, abilityScores, newProf, level);
    onUpdate({ proficient: newProf, modifier: mod });
  }, [proficient, ability, abilityScores, level, onUpdate]);

  const handleManualValue = useCallback(
    (index: number, raw: string) => {
      const v = raw === '' ? null : Math.max(1, Math.min(20, parseInt(raw, 10) || 1));
      const next = [...manualValues];
      next[index] = v;
      onUpdate({ manualValues: next });
    },
    [manualValues, onUpdate],
  );

  const canSubmitManual = manualValues.every((v) => v != null && v >= 1 && v <= 20);

  const handleSubmit = useCallback(() => {
    if (mode === 'manual') {
      onSubmit(manualValues.filter((v): v is number => v != null));
    } else {
      onSubmit();
    }
  }, [mode, manualValues, onSubmit]);

  const handleAutoRoll = useCallback(() => {
    onSubmit();
  }, [onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Enter' && mode === 'manual' && canSubmitManual && !submitting) handleSubmit();
    },
    [onClose, mode, canSubmitManual, submitting, handleSubmit],
  );

  const modSign = modifier >= 0 ? '+' : '';

  return (
    <m.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/80 backdrop-blur-sm"
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <m.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        className="panel-glow w-full max-w-md p-5 space-y-4"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dice-modal-title"
      >
        <h2 id="dice-modal-title" className="font-display text-lg text-gray-100">
          {label}
        </h2>

        {showAbilityPicker && (
          <div className="space-y-1">
            <p className="text-xs text-muted uppercase tracking-wider">Ability</p>
            <div className="flex gap-1.5">
              {ABILITIES.map((ab) => (
                <button
                  key={ab}
                  type="button"
                  onClick={() => handleAbilityChange(ab)}
                  className={`flex-1 py-1.5 rounded-md text-sm font-semibold uppercase transition-colors ${
                    ability === ab
                      ? 'bg-accent/15 text-accent border border-accent/25'
                      : 'text-muted hover:text-gray-200 border border-border'
                  }`}
                >
                  {ab}
                </button>
              ))}
            </div>
            {hasModifier && (
              <p className="text-xs text-muted">
                {ability.toUpperCase()} {abilityScores[ability] ?? 10} → modifier{' '}
                <span className="text-gray-200 font-semibold">
                  {modSign}
                  {modifier}
                </span>
              </p>
            )}
          </div>
        )}

        {showProficiency && (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={proficient}
              onChange={handleProficiencyToggle}
              className="accent-accent w-4 h-4"
            />
            <span className="text-sm text-gray-300">Proficient</span>
          </label>
        )}

        {shortcutId !== 'death_save' && (
          <div className="space-y-1">
            <p className="text-xs text-muted uppercase tracking-wider">Advantage</p>
            <SegmentedControl value={advantage} onChange={handleAdvantageChange} options={ADVANTAGE_OPTIONS} />
          </div>
        )}

        <SegmentedControl
          value={mode}
          onChange={(v) => onUpdate({ mode: v as 'manual' | 'auto', autoResult: null })}
          options={MODE_OPTIONS}
        />

        {mode === 'manual' && (
          <DiceRollManualSection
            diceCount={diceCount}
            advantage={advantage}
            manualValues={manualValues}
            hasModifier={hasModifier}
            modifier={modifier}
            canSubmitManual={canSubmitManual}
            onManualValue={handleManualValue}
          />
        )}

        {mode === 'auto' && (
          <DiceRollAutoSection
            diceCount={diceCount}
            advantage={advantage}
            hasModifier={hasModifier}
            modifier={modifier}
            autoResult={autoResult}
            rolling={rolling}
            onAutoRoll={handleAutoRoll}
          />
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-ghost" onClick={onClose} disabled={submitting || rolling}>
            Cancel
          </button>
          {mode === 'manual' && (
            <button
              type="button"
              className="btn-primary"
              onClick={handleSubmit}
              disabled={!canSubmitManual || submitting}
            >
              {submitting ? 'Rolling…' : 'Accept'}
            </button>
          )}
        </div>
      </m.div>
    </m.div>
  );
}
