import type { Character } from '../../types';
import { displayLabel, EMPTY_FIELD } from '../../lib/displayText';
import GlossaryTip, { GlossaryTagList } from '../ui/GlossaryTip';
import { ABILITIES, SKILLS } from './sheetConstants';
import {
  formatMod,
  initiativeMod,
  passivePerception,
  proficiencyBonus,
  saveBonus,
  skillBonus,
  spellAttackBonus,
  spellAbility,
  spellSaveDc,
} from './sheetUtils';
import { AbilityTile, CombatStat, DeathSaves, HpBar, SheetField, SheetSection } from './characterSheetViewParts';

interface Page1Props {
  character: Character;
  editable?: boolean;
  onChange?: (patch: Partial<Character>) => void;
}

export default function CharacterSheetPage1({ character: c, editable, onChange }: Page1Props) {
  const scores = c.ability_scores || {};
  const profs = new Set(c.skill_proficiencies || []);
  const saves = new Set(c.save_proficiencies || []);
  const pb = proficiencyBonus(c.level || 1);
  const spellAb = spellAbility(c.class_name || '');
  const spellDc = spellSaveDc(c);
  const spellAtk = spellAttackBonus(c);
  const hitDiceMax = Number(c.hit_dice_max ?? c.level ?? 1);
  const hitDiceSpent = Number(c.hit_dice_spent ?? 0);

  const classLine =
    (c.classes?.length ? c.classes : [{ class_name: c.class_name, level: c.level, subclass: c.subclass }])
      .map((e) => `${displayLabel(e.class_name)} ${e.level}${e.subclass ? ` (${displayLabel(e.subclass)})` : ''}`)
      .join(' · ') ||
    displayLabel(c.class_name) ||
    EMPTY_FIELD;

  const patch = (p: Partial<Character>) => onChange?.({ ...c, ...p });

  const header = (
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

  return (
    <div className="space-y-4">
      {header}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <SheetSection title="Abilities" className="lg:col-span-3">
          <div className="grid grid-cols-2 gap-2">
            {ABILITIES.map((ab) => (
              <AbilityTile
                key={ab}
                ab={ab}
                score={scores[ab] ?? 10}
                save={saveBonus(c, ab)}
                proficient={saves.has(ab)}
              />
            ))}
          </div>
        </SheetSection>

        <SheetSection title="Skills" className="lg:col-span-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
            {SKILLS.map((sk) => (
              <div
                key={sk.id}
                className={`flex items-center justify-between text-sm py-0.5 px-1 rounded ${
                  profs.has(sk.id) ? 'text-gray-100 bg-accent/5' : 'text-muted'
                }`}
              >
                <span className="flex items-center gap-1.5 min-w-0">
                  <span className={profs.has(sk.id) ? 'text-accent' : 'text-border'}>
                    {profs.has(sk.id) ? '●' : '○'}
                  </span>
                  <GlossaryTip name={sk.id} variant="custom">
                    <span className="truncate cursor-pointer">{sk.label}</span>
                  </GlossaryTip>
                </span>
                <span
                  className={`tabular-nums shrink-0 ml-2 ${profs.has(sk.id) ? 'font-semibold text-accent/90' : ''}`}
                >
                  {skillBonus(c, sk.id, sk.ability)}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-border flex justify-between text-sm">
            <span className="text-muted">Passive Perception</span>
            <span className="font-semibold text-accent">{passivePerception(c)}</span>
          </div>
        </SheetSection>

        <div className="lg:col-span-4 space-y-4">
          <SheetSection title="Combat">
            <div className="grid grid-cols-3 gap-2 mb-3">
              <CombatStat label="Armor Class" value={String(c.ac ?? 10)} accent />
              <CombatStat label="Initiative" value={formatMod(initiativeMod(c))} />
              <CombatStat label="Speed" value={`${c.speed ?? 30} ft`} />
            </div>
            <SheetField
              label="Hit Points"
              value={`${c.hp ?? 0} / ${c.max_hp ?? 0}`}
              editable={editable}
              onChange={(v) => {
                const [cur, max] = v.split('/').map((s) => parseInt(s.trim()) || 0);
                patch({ hp: cur, max_hp: max || c.max_hp });
              }}
              mono
            />
            <HpBar hp={c.hp ?? 0} maxHp={c.max_hp ?? 0} />
            <div className="grid grid-cols-2 gap-3 mt-3">
              <SheetField label="Hit Dice" value={`${hitDiceMax - hitDiceSpent}d${c.hit_die ?? 8}`} mono />
              <div className="sheet-field flex items-center justify-between">
                <div>
                  <div className="sheet-label">Heroic Inspiration</div>
                  {String(c.species || '').toLowerCase() === 'human' && (
                    <div className="text-[9px] text-muted mt-0.5">Resourceful · Long Rest</div>
                  )}
                  <div className="text-xl mt-0.5">{c.heroic_inspiration ? '★' : '☆'}</div>
                </div>
              </div>
            </div>
            <div className="mt-3">
              <DeathSaves
                successes={Number(c.death_save_successes ?? 0)}
                failures={Number(c.death_save_failures ?? 0)}
              />
            </div>
          </SheetSection>

          {spellDc !== null && (
            <SheetSection title="Spellcasting">
              <div className="grid grid-cols-3 gap-2">
                <CombatStat label="Save DC" value={String(spellDc)} accent />
                <CombatStat label="Attack" value={formatMod(spellAtk ?? 0)} />
                <CombatStat label="Ability" value={spellAb?.toUpperCase() || EMPTY_FIELD} />
              </div>
            </SheetSection>
          )}

          <SheetSection title="Features & Gear">
            <div className="space-y-3">
              <div>
                <div className="sheet-label mb-1.5">Cantrips</div>
                <GlossaryTagList items={c.cantrips || []} classId={c.class_name} />
              </div>
              <div>
                <div className="sheet-label mb-1.5">Feats</div>
                <GlossaryTagList
                  items={[c.origin_feat, c.versatile_origin_feat, ...(c.feats || [])].filter(Boolean) as string[]}
                />
              </div>
              <div>
                <div className="sheet-label mb-1.5">Weapons</div>
                {(c.weapons || []).length ? (
                  <div className="flex flex-wrap gap-1.5">
                    {(c.weapons || []).map((w) => (
                      <GlossaryTip key={w.name} name={w.name} />
                    ))}
                  </div>
                ) : (
                  <span className="text-sm text-muted">{EMPTY_FIELD}</span>
                )}
              </div>
              {c.subclass &&
                (editable ? (
                  <SheetField
                    label="Subclass"
                    value={c.subclass}
                    editable={editable}
                    onChange={(v) => patch({ subclass: v })}
                  />
                ) : (
                  <div>
                    <div className="sheet-label mb-1">Subclass</div>
                    <GlossaryTip name={c.subclass} variant="inline" className="text-sm font-medium" />
                  </div>
                ))}
            </div>
          </SheetSection>
        </div>
      </div>
    </div>
  );
}
