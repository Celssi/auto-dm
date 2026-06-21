"""D&D 5e shortcuts."""

from __future__ import annotations

from typing import Literal

from backend.characters.character_builder import apply_short_rest, long_rest_recover
from backend.characters.entity import Dnd5eCharacter, character_from_dict, character_to_dict
from backend.dm.audit import record_audit
from backend.dm.curated import roll_oracle
from backend.dm.dice import roll_advantage_d20, roll_death_saves
from backend.dm.resource_keeper import apply_cast_spell_shortcut
from backend.play_tools import roll_dice

GAME_ID = "dnd5e"

ShortcutKind = Literal["roll", "roll_rag", "rag_only", "static"]

SHORTCUTS: list[dict[str, str]] = [
    {"id": "ability_check", "label": "Ability check", "kind": "roll_rag"},
    {"id": "saving_throw", "label": "Saving throw", "kind": "roll_rag"},
    {"id": "attack_roll", "label": "Attack roll", "kind": "roll_rag"},
    {"id": "initiative", "label": "Initiative", "kind": "roll"},
    {"id": "death_save", "label": "Death save", "kind": "roll"},
    {"id": "oracle", "label": "Oracle (d6 yes/no)", "kind": "roll"},
    {"id": "short_rest", "label": "Short rest", "kind": "roll_rag"},
    {"id": "long_rest", "label": "Long rest", "kind": "roll_rag"},
    {"id": "cast_spell", "label": "Cast spell", "kind": "static"},
    {"id": "rules_help", "label": "D&D 5e rules help", "kind": "rag_only"},
]

SHORTCUT_IDS = frozenset(s["id"] for s in SHORTCUTS)


def match_dnd5e_shortcut(text: str) -> str | None:
    lower = text.lower().strip()
    if "ability check" in lower or "skill check" in lower:
        return "ability_check"
    if "saving throw" in lower or "save roll" in lower:
        return "saving_throw"
    if "attack roll" in lower or ("attack" in lower and "dnd" in lower):
        return "attack_roll"
    if "initiative" in lower:
        return "initiative"
    if "death save" in lower:
        return "death_save"
    if "oracle" in lower or ("d6" in lower and ("yes" in lower or "no" in lower)):
        return "oracle"
    if "short rest" in lower:
        return "short_rest"
    if "long rest" in lower:
        return "long_rest"
    if lower.startswith("/cast ") or (lower.startswith("cast ") and len(lower.split()) >= 2):
        return "cast_spell"
    if "dnd rules" in lower or "d&d rules" in lower or "how to play dnd" in lower:
        return "rules_help"
    return None


def _resolve_modifier(
    ability: str,
    ability_scores: dict | None,
    modifier: int | None,
    proficient: bool,
    level: int,
) -> int:
    if modifier is not None:
        return int(modifier)
    scores = ability_scores or {}
    score = int(scores.get(ability.lower(), 10) or 10)
    mod = (score - 10) // 2
    if proficient:
        mod += 2 + (max(1, int(level or 1)) - 1) // 4
    return mod


def _char_from_kwargs(**kwargs) -> Dnd5eCharacter:
    return character_from_dict(
        {
            "name": kwargs.get("name", ""),
            "species": kwargs.get("species", ""),
            "class_name": kwargs.get("class_name", ""),
            "level": kwargs.get("level", 1),
            "hp": kwargs.get("hp", 0),
            "max_hp": kwargs.get("max_hp", 0),
            "hit_die": kwargs.get("hit_die", 8),
            "hit_dice_max": kwargs.get("hit_dice_max", kwargs.get("level", 1)),
            "hit_dice_spent": kwargs.get("hit_dice_spent", 0),
            "ability_scores": kwargs.get("ability_scores") or {},
            "spell_slots": kwargs.get("spell_slots") or {},
            "origin_feat": kwargs.get("origin_feat", ""),
            "versatile_origin_feat": kwargs.get("versatile_origin_feat", ""),
        }
    )


def run_shortcut(
    shortcut_id: str,
    *,
    game_id: str = GAME_ID,
    name: str = "",
    species: str = "",
    class_name: str = "",
    level: int = 1,
    hp: int = 0,
    max_hp: int = 0,
    ac: int = 10,
    hit_die: int = 8,
    hit_dice_max: int = 0,
    hit_dice_spent: int = 0,
    ability_scores: dict | None = None,
    spell_slots: dict | None = None,
    ability: str = "dex",
    modifier: int | None = None,
    proficient: bool = False,
    advantage: str = "normal",
    target_ac: int | None = None,
    hit_dice_to_spend: int = 1,
    death_save_successes: int = 0,
    death_save_failures: int = 0,
    pre_rolled: list[int] | None = None,
    **_kwargs,
) -> dict:
    _ = game_id, ac
    who = name.strip() or "the character"
    build = f"{who}"
    if species or class_name:
        build = f"{who} ({species} {class_name} {level})".strip()

    if shortcut_id == "ability_check":
        mod = _resolve_modifier(ability, ability_scores, modifier, proficient, level)
        adv = advantage if advantage in ("normal", "advantage", "disadvantage") else "normal"
        result = roll_advantage_d20(mod, advantage=adv, pre_rolled=pre_rolled)  # type: ignore[arg-type]
        prof = " (proficient)" if proficient else ""
        user = f"**Ability check** ({ability.upper()}{prof})\n\n{result['summary']}"
        prompt = (
            f"D&D 5e ability check for {build}, {ability.upper()} modifier {mod:+d}. "
            f"{result['summary']}. Explain DC, success, and any relevant 2024 PHB guidance."
        )
        return {"user_message": user, "prompt": prompt, "dice": result, "task": "ability_check"}

    if shortcut_id == "saving_throw":
        mod = _resolve_modifier(ability, ability_scores, modifier, proficient, level)
        adv = advantage if advantage in ("normal", "advantage", "disadvantage") else "normal"
        result = roll_advantage_d20(mod, advantage=adv, pre_rolled=pre_rolled)  # type: ignore[arg-type]
        user = f"**Saving throw** ({ability.upper()})\n\n{result['summary']}"
        prompt = (
            f"D&D 5e saving throw for {build}, {ability.upper()} save {mod:+d}. "
            f"{result['summary']}. Explain save DC, success, and effects using PHB rules."
        )
        return {"user_message": user, "prompt": prompt, "dice": result, "task": "saving_throw"}

    if shortcut_id == "attack_roll":
        mod = _resolve_modifier(ability, ability_scores, modifier, proficient, level)
        adv = advantage if advantage in ("normal", "advantage", "disadvantage") else "normal"
        result = roll_advantage_d20(mod, advantage=adv, pre_rolled=pre_rolled)  # type: ignore[arg-type]
        if target_ac is not None:
            ac_note = f"\n\nvs target AC **{int(target_ac)}**"
            ac_prompt = f" vs AC {int(target_ac)}"
        else:
            ac_note = "\n\n(Set target AC when you know the foe's armor class.)"
            ac_prompt = " vs DM-set AC"
        user = f"**Attack roll**\n\n{result['summary']}{ac_note}"
        prompt = (
            f"D&D 5e attack roll for {build}, attack bonus {mod:+d}{ac_prompt}. "
            f"{result['summary']}. Explain hit, critical hit, and damage next steps."
        )
        return {"user_message": user, "prompt": prompt, "dice": result, "task": "attack_roll"}

    if shortcut_id == "initiative":
        char = _char_from_kwargs(**_kwargs)
        mod = int(modifier) if modifier is not None else char.initiative_modifier()
        if pre_rolled is not None:
            from backend.dm.dice import _build_d20_result

            result = _build_d20_result(pre_rolled, mod, "normal")
        else:
            result = roll_dice(f"1d20{mod:+d}" if mod else "1d20", caller="shortcut.initiative")
        total = int(result.get("total", 0))
        user = f"**Initiative**\n\n{result.get('summary', f'd20+{mod} = {total}')}"
        return {"user_message": user, "prompt": user, "static": True, "dice": result}

    if shortcut_id == "death_save":
        before_char = {
            "hp": hp,
            "max_hp": max_hp,
            "death_save_successes": death_save_successes,
            "death_save_failures": death_save_failures,
        }
        result = roll_death_saves(pre_rolled=pre_rolled[0] if pre_rolled else None)
        roll = int(result.get("roll", 0))
        succ = max(0, min(3, int(death_save_successes)))
        fail = max(0, min(3, int(death_save_failures)))
        updates: dict = {}
        status = ""
        if roll == 20:
            succ, fail = 0, 0
            status = "**Natural 20: regain 1 HP and wake up!**"
            updates = {"hp": 1, "death_save_successes": 0, "death_save_failures": 0}
        else:
            if roll == 1:
                fail = min(3, fail + 2)
            elif roll >= 10:
                succ = min(3, succ + 1)
            else:
                fail = min(3, fail + 1)
            if succ >= 3:
                status = "**Three successes: stable** (still at 0 HP)."
                updates = {"death_save_successes": 0, "death_save_failures": 0}
            elif fail >= 3:
                status = "**Three failures: the character dies.**"
                updates = {"death_save_successes": 0, "death_save_failures": 3}
            else:
                updates = {"death_save_successes": succ, "death_save_failures": fail}
        after_char = {**before_char, **updates}
        record_audit(
            {
                "event": "death_save",
                "source": "shortcut",
                "before": before_char,
                "after": after_char,
                "detail": {
                    "roll": roll,
                    "successes": after_char.get("death_save_successes", succ),
                    "failures": after_char.get("death_save_failures", fail),
                    "outcome": result.get("outcome"),
                    "inferred": False,
                },
            }
        )
        tally = f"Successes {min(succ, 3)}/3 · Failures {min(fail, 3)}/3"
        user = f"**Death save** (HP {hp}/{max_hp})\n\n{result['summary']}\n\n{tally}"
        if status:
            user += f"\n\n{status}"
        prompt = (
            f"D&D 5e death saving throw for {build} at {hp}/{max_hp} HP. "
            f"{result['summary']}. Running tally: {tally}. {status} "
            "Explain death save rules and what happens next."
        )
        return {
            "user_message": user,
            "prompt": prompt,
            "dice": result,
            "entity_updates": updates,
            "task": "death_save",
        }

    if shortcut_id == "oracle":
        result = roll_oracle()
        user = f"**Solo oracle (d6)**\n\n{result['summary']}"
        return {
            "user_message": user,
            "prompt": user,
            "static": True,
            "dice": result,
            "task": "oracle",
        }

    if shortcut_id == "short_rest":
        char = _char_from_kwargs(
            name=name,
            species=species,
            class_name=class_name,
            level=level,
            hp=hp,
            max_hp=max_hp,
            hit_die=hit_die,
            hit_dice_max=hit_dice_max or level,
            hit_dice_spent=hit_dice_spent,
            ability_scores=ability_scores,
            spell_slots=spell_slots,
        )
        char = character_from_dict(
            {
                **character_to_dict(char),
                "classes": _kwargs.get("classes") or [],
                "subclass": _kwargs.get("subclass") or "",
            }
        )
        rest = apply_short_rest(char, dice_to_spend=hit_dice_to_spend)
        user = f"**Short rest**\n\n{rest['summary']}"
        prompt = (
            f"D&D 5e short rest for {build}. {rest['summary']}. "
            "Explain remaining short rest options: more Hit Dice, class features, "
            "and limitations per 2024 PHB."
        )
        return {
            "user_message": user,
            "prompt": prompt,
            "dice": {"summary": rest["summary"]},
            "entity_updates": rest.get("entity_updates") or {},
            "task": "short_rest",
        }

    if shortcut_id == "long_rest":
        char = _char_from_kwargs(
            name=name,
            species=species,
            class_name=class_name,
            level=level,
            hp=hp,
            max_hp=max_hp,
            hit_die=hit_die,
            hit_dice_max=hit_dice_max or level,
            hit_dice_spent=hit_dice_spent,
            ability_scores=ability_scores,
            spell_slots=spell_slots,
        )
        rest = long_rest_recover(char)
        user = f"**Long rest**\n\n{rest['summary']}"
        trance_dm = ""
        if (species or "").strip().lower() == "elf":
            trance_dm = (
                " The character is an elf: narrate this as a 4-hour Trance "
                "(meditative rest, not sleep), per PHB 2024 Trance trait. "
            )
        prompt = (
            f"D&D 5e long rest for {build}. {rest['summary']}.{trance_dm} "
            "Explain long rest limits and anything not recovered per 2024 PHB."
        )
        return {
            "user_message": user,
            "prompt": prompt,
            "static": False,
            "rag_only": True,
            "entity_updates": rest.get("entity_updates") or {},
            "task": "long_rest",
        }

    if shortcut_id == "cast_spell":
        spell_name = str(_kwargs.get("spell_name") or "").strip()
        char_dict = character_to_dict(
            character_from_dict(
                {
                    "name": name,
                    "species": species,
                    "class_name": class_name,
                    "subclass": _kwargs.get("subclass") or "",
                    "level": level,
                    "hp": hp,
                    "max_hp": max_hp,
                    "hit_die": hit_die,
                    "spell_slots": spell_slots or {},
                    "cantrips": _kwargs.get("cantrips") or [],
                    "prepared_spells": _kwargs.get("prepared_spells") or [],
                    "known_spells": _kwargs.get("known_spells") or [],
                    "classes": _kwargs.get("classes") or [],
                    "wild_shape_uses": int(_kwargs.get("wild_shape_uses") or 0),
                    "concentration": _kwargs.get("concentration") or "",
                }
            )
        )
        slot_level = int(_kwargs.get("slot_level") or 0)
        entity, logs = apply_cast_spell_shortcut(
            char_dict,
            spell_name,
            slot_level=slot_level,
            ritual=bool(_kwargs.get("ritual")),
        )
        summary = logs[0] if logs else f"Cast {spell_name or '(no spell)'}."
        user = f"**Cast spell**\n\n{summary}"
        return {
            "user_message": user,
            "prompt": user,
            "static": True,
            "summary": summary,
            "entity_updates": entity,
            "task": "cast_spell",
        }

    if shortcut_id == "rules_help":
        prompt = (
            "Explain how to run D&D 5e solo as player and DM: ability checks, saves, combat, "
            "rests, death saves, and using oracle tables for unknown outcomes. "
            "Reference Player's Handbook and DMG; use Faerûn "
            "supplements only when the campaign is set in Faerûn."
        )
        return {"user_message": "**D&D 5e rules**", "prompt": prompt, "rag_only": True}

    return {"user_message": "Unknown shortcut.", "prompt": "Unknown shortcut.", "static": True}
