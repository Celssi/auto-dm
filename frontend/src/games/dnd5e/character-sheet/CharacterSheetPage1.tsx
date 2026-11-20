import type { Character } from '../../../types';
import { EMPTY_FIELD } from '../../../lib/displayText';
import GlossaryTip, { GlossaryTagList } from '../../../components/ui/GlossaryTip';
import { ABILITIES, SKILLS } from './sheetConstants';
import { LabelWithTip } from '../../../components/ui/HelpTip';
import {
  ARMOR_CATALOG,
  computeAcDetails,
  formatMod,
  initiativeMod,
  passivePerception,
  saveBonus,
  skillBonus,
  spellAttackBonus,
  spellAbility,
  spellSaveDc,
  expertiseSkills,
  uniqueFeatLabels,
  weaponAttackLine,
  characterHasWeaponMastery,
} from './sheetUtils';
import {
  AbilityTile,
  CombatStat,
  ConditionList,
  DeathSaves,
  HpBar,
  SheetField,
  SheetSection,
} from './characterSheetViewParts';
import CharacterSheetHeader from './CharacterSheetHeader';

interface Page1Props {
  character: Character;
  editable?: boolean;
  onChange?: (patch: Partial<Character>) => void;
  hideHeader?: boolean;
}

export default function CharacterSheetPage1({ character: c, editable, onChange, hideHeader }: Page1Props) {
  const liveScores = c.ability_scores || {};
  const baseScores = c.base_ability_scores || {};
  const liveLooksUnset = (['str', 'dex', 'con', 'int', 'wis', 'cha'] as const).every(
    (key) => Number(liveScores[key] ?? 10) === 10,
  );
  const scores =
    liveLooksUnset && Object.keys(baseScores).length
      ? { ...liveScores, ...baseScores }
      : { ...baseScores, ...liveScores };
  const profs = new Set(c.skill_proficiencies || []);
  const saves = new Set(c.save_proficiencies || []);
  const spellAb = spellAbility(c.class_name || '');
  const spellDc = spellSaveDc(c);
  const spellAtk = spellAttackBonus(c);
  const hitDiceMax = Number(c.hit_dice_max ?? c.level ?? 1);
  const hitDiceSpent = Number(c.hit_dice_spent ?? 0);

  const patch = (p: Partial<Character>) => onChange?.({ ...c, ...p });

  return (
    <>
      {!hideHeader && <CharacterSheetHeader character={c} editable={editable} onChange={onChange} />}
      <Page1Abilities scores={scores} character={c} saves={saves} editable={editable} onPatch={patch} />
      <Page1Skills character={c} profs={profs} />
      <Page1Combat
        character={c}
        editable={editable}
        hitDiceMax={hitDiceMax}
        hitDiceSpent={hitDiceSpent}
        onPatch={patch}
      />
      {spellDc !== null && (
        <SheetSection title="Spellcasting">
          <div className="grid grid-cols-3 gap-2">
            <CombatStat label="Save DC" value={String(spellDc)} accent />
            <CombatStat label="Attack" value={formatMod(spellAtk ?? 0)} />
            <CombatStat label="Ability" value={spellAb?.toUpperCase() || EMPTY_FIELD} />
          </div>
        </SheetSection>
      )}
      <Page1FeaturesGear character={c} editable={editable} onPatch={patch} />
    </>
  );
}

function Page1Abilities({
  scores,
  character: c,
  saves,
  editable,
  onPatch,
}: {
  scores: Record<string, number>;
  character: Character;
  saves: Set<string>;
  editable?: boolean;
  onPatch: (p: Partial<Character>) => void;
}) {
  return (
    <SheetSection title="Abilities">
      <div className="grid grid-cols-2 gap-2">
        {ABILITIES.map((ab) => (
          <AbilityTile
            key={ab}
            ab={ab}
            score={scores[ab] ?? 10}
            save={saveBonus(c, ab)}
            proficient={saves.has(ab)}
            editable={editable}
            onScoreChange={(score) => {
              const next = { ...(c.base_ability_scores || c.ability_scores), [ab]: score };
              onPatch({
                base_ability_scores: next,
                ability_scores: { ...c.ability_scores, [ab]: score },
                ability_scores_set: true,
              });
            }}
          />
        ))}
      </div>
      {editable && (
        <p className="text-[11px] text-muted mt-2 leading-relaxed">
          Editing a score here changes the stored base. Background ability increases still apply on save.
        </p>
      )}
    </SheetSection>
  );
}

function Page1Skills({ character: c, profs }: { character: Character; profs: Set<string> }) {
  const expertise = expertiseSkills(c);
  return (
    <SheetSection title="Skills">
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
                {expertise.has(sk.id) ? '●●' : profs.has(sk.id) ? '●' : '○'}
              </span>
              <GlossaryTip name={sk.id} variant="custom">
                <span className="truncate cursor-pointer">{sk.label}</span>
              </GlossaryTip>
            </span>
            <span className={`tabular-nums shrink-0 ml-2 ${profs.has(sk.id) ? 'font-semibold text-accent/90' : ''}`}>
              {skillBonus(c, sk.id, sk.ability)}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-border flex justify-between text-sm">
        <LabelWithTip id="passive-perception" label="Passive Perception" className="text-muted" />
        <span className="font-semibold text-accent">{passivePerception(c)}</span>
      </div>
    </SheetSection>
  );
}

function shownArmorClass(character: Character, computedAc: number) {
  if (!character.ac_manual) return computedAc;
  return Number(character.ac ?? computedAc);
}

function CombatArmorFields({
  character: c,
  shownAc,
  onPatch,
}: {
  character: Character;
  shownAc: number;
  onPatch: (p: Partial<Character>) => void;
}) {
  return (
    <div className="space-y-2 mb-3">
      <label className="block">
        <span className="sheet-label">Worn armor</span>
        <select
          className="select w-full mt-1"
          value={String(c.armor || 'none')}
          onChange={(e) =>
            onPatch({
              armor: e.target.value,
              ac_manual: false,
              ac: computeAcDetails({ ...c, armor: e.target.value, ac_manual: false }).ac,
            })
          }
          aria-label="Worn armor"
        >
          {ARMOR_CATALOG.map((row) => (
            <option key={row.id} value={row.id}>
              {row.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm text-gray-300">
        <input
          type="checkbox"
          className="rounded border-border"
          checked={Boolean(c.shield)}
          onChange={(e) =>
            onPatch({
              shield: e.target.checked,
              ac_manual: false,
              ac: computeAcDetails({ ...c, shield: e.target.checked, ac_manual: false }).ac,
            })
          }
        />
        Shield (+2 AC)
      </label>
      <label className="flex items-center gap-2 text-sm text-gray-300">
        <input
          type="checkbox"
          className="rounded border-border"
          checked={Boolean(c.ac_manual)}
          onChange={(e) => onPatch({ ac_manual: e.target.checked, ac: shownAc })}
        />
        Set AC manually
      </label>
      {c.ac_manual ? (
        <input
          type="number"
          min={1}
          max={30}
          className="w-20 bg-transparent border-b border-border focus:border-accent/40 text-lg font-semibold"
          value={shownAc}
          onChange={(e) =>
            onPatch({ ac: Math.max(1, Math.min(30, parseInt(e.target.value, 10) || 10)), ac_manual: true })
          }
          aria-label="Armor Class"
        />
      ) : null}
    </div>
  );
}

function parseHpPair(value: string, fallbackMax: number) {
  const [cur, max] = value.split('/').map((part) => parseInt(part.trim(), 10) || 0);
  return { hp: cur, max_hp: max || fallbackMax };
}

function CombatResources({
  character: c,
  hitDiceMax,
  hitDiceSpent,
}: {
  character: Character;
  hitDiceMax: number;
  hitDiceSpent: number;
}) {
  const exhaustion = Number(c.exhaustion ?? 0);
  const hitDie = c.hit_die ?? 8;
  return (
    <>
      <div className="mt-2">
        <LabelWithTip id="exhaustion" label="Exhaustion" />
        <div className="sheet-value font-mono mt-0.5">
          Level {exhaustion}
          {exhaustion >= 6 ? ' (dead)' : ''}
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 items-start">
        <div>
          <LabelWithTip id="hit-dice" label="Hit Dice" />
          <div className="sheet-value font-mono mt-0.5">{`${hitDiceMax - hitDiceSpent}d${hitDie}`}</div>
        </div>
        <div>
          <LabelWithTip id="heroic-inspiration" label="Heroic Inspiration" />
          <div className="sheet-value mt-0.5 inline-flex items-center gap-1.5">
            <span aria-hidden="true">{c.heroic_inspiration ? '★' : '☆'}</span>
            <span>{c.heroic_inspiration ? 'Yes' : 'No'}</span>
          </div>
          {String(c.species || '').toLowerCase() === 'human' ? (
            <p className="text-[10px] text-muted leading-snug mt-0.5">Resourceful, Long Rest</p>
          ) : null}
        </div>
      </div>
      <div className="mt-3">
        <ConditionList conditions={c.conditions} />
      </div>
      <div className="mt-3">
        <DeathSaves successes={Number(c.death_save_successes ?? 0)} failures={Number(c.death_save_failures ?? 0)} />
      </div>
    </>
  );
}

function Page1Combat({
  character: c,
  editable,
  hitDiceMax,
  hitDiceSpent,
  onPatch,
}: {
  character: Character;
  editable?: boolean;
  hitDiceMax: number;
  hitDiceSpent: number;
  onPatch: (p: Partial<Character>) => void;
}) {
  const ac = computeAcDetails(c);
  const shownAc = shownArmorClass(c, ac.ac);
  const speed = c.speed_effective ?? c.speed ?? 30;
  const hpLabel = `${c.hp ?? 0} / ${c.max_hp ?? 0}`;
  return (
    <SheetSection title="Combat">
      <div className="grid grid-cols-3 gap-2 mb-3">
        <CombatStat label="Armor Class" value={String(shownAc)} accent tipId="armor-class" />
        <CombatStat label="Initiative" value={formatMod(initiativeMod(c))} tipId="initiative" />
        <CombatStat label="Speed" value={`${speed} ft`} tipId="speed" />
      </div>
      <p className="text-[11px] text-muted mb-3 leading-relaxed">{ac.formula}</p>
      {editable ? <CombatArmorFields character={c} shownAc={shownAc} onPatch={onPatch} /> : null}
      <SheetField
        label="Hit Points"
        value={hpLabel}
        editable={editable}
        onChange={(value) => onPatch(parseHpPair(value, c.max_hp ?? 0))}
        mono
      />
      <HpBar hp={c.hp ?? 0} maxHp={c.max_hp ?? 0} />
      <CombatResources character={c} hitDiceMax={hitDiceMax} hitDiceSpent={hitDiceSpent} />
    </SheetSection>
  );
}

function Page1FeaturesGear({
  character: c,
  editable,
  onPatch,
}: {
  character: Character;
  editable?: boolean;
  onPatch: (p: Partial<Character>) => void;
}) {
  const weapons = c.weapons || [];
  return (
    <SheetSection title="Features & Gear">
      <div className="space-y-3">
        <div>
          <div className="sheet-label mb-1.5">Cantrips</div>
          <GlossaryTagList items={c.cantrips || []} classId={c.class_name} />
        </div>
        <div>
          <LabelWithTip id="feats" label="Feats" className="sheet-label mb-1.5" />
          <GlossaryTagList
            items={uniqueFeatLabels([c.origin_feat, c.versatile_origin_feat, ...(c.feats || [])])}
          />
        </div>
        <div>
          <div className="sheet-label mb-1.5">Weapons</div>
          {weapons.length ? (
            <div className="space-y-1.5">
              {weapons.map((w) => (
                <div key={w.name} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  {characterHasWeaponMastery(c) ? (
                    <GlossaryTip name={w.name} />
                  ) : (
                    <span className="text-sm font-medium">{w.name}</span>
                  )}
                  <span className="text-xs text-muted">{weaponAttackLine(c, w)}</span>
                </div>
              ))}
            </div>
          ) : (
            <span className="text-sm text-muted">{EMPTY_FIELD}</span>
          )}
        </div>
        <div>
          <LabelWithTip id="weapon-mastery" label="Weapon Mastery" className="sheet-label mb-1.5" />
          {(c.weapon_mastery || []).length > 0 ? (
            <GlossaryTagList items={c.weapon_mastery || []} />
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
              onChange={(v) => onPatch({ subclass: v })}
            />
          ) : (
            <div>
              <div className="sheet-label mb-1">Subclass</div>
              <GlossaryTip name={c.subclass} variant="inline" className="text-sm font-medium" />
            </div>
          ))}
      </div>
    </SheetSection>
  );
}
