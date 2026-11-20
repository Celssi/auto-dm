"""D&D 5e DM agent nodes."""

from __future__ import annotations

import re

from backend.dm.encounters import CombatState, combat_state_view, load_combat_state
from backend.dm.narration_stream import (
    emit_narration,
    emit_ready,
    emit_sheet,
    narration_enabled,
)
from backend.dm.prose_style import sanitize_narration_dashes
from backend.dm.state import DMState, char_from_dict, factions_for, game_plugin
from backend.dm.story_director import (
    apply_completion_if_done,
    build_narrator_brief,
    ensure_story_progress,
    load_story_progress,
    player_progress_view,
    save_story_progress,
    update_progress_after_turn,
)
from backend.dm.story_memory import build_narrative_context
from backend.dm.trace import log_agent
from backend.dm.turn_kind import is_dice_only_turn
from backend.games.dnd5e.actions import SHORTCUTS
from backend.games.dnd5e.dm.combat_manager import (
    finish_player_turn,
    format_combat_context,
    try_start_planned_encounter,
)
from backend.games.dnd5e.prompts import (
    dnd5e_session_context,
    dnd5e_stable_system_prompt,
    dnd5e_turn_context,
)
from backend.llm import (
    build_cached_chat_messages,
    get_langchain_chat_llm,
    invoke_chat_llm,
    message_text,
    stream_chat_llm,
)

COMBAT_SHORTCUTS = frozenset({"attack_roll", "initiative", "death_save"})
COMBAT_KEYWORDS = (
    "attack",
    "combat",
    "fight",
    "initiative",
    "damage",
    "hp",
    "hit point",
    "death save",
    "spell slot",
    "cast ",
    "enemy",
    "monster",
)

_RESOURCE_SIGNALS = (
    "cast ",
    "/cast ",
    "spell slot",
    "concentrat",
    "wild shape",
    "short rest",
    "long rest",
    "hit dice",
    "hit point",
    " hp",
    "hp ",
    "hp/",
    "falling",
    "prone",
    "damage",
    "ritual",
)

_MIN_RESPONSE_FOR_BOOKKEEPING = 120


def _needs_rules_check(message: str) -> bool:
    lower = message.lower()
    if "rules help" in lower or lower.startswith("/rules"):
        return True
    return any(
        phrase in lower
        for phrase in ("how does", "how do i", "what is the rule", "what's the rule", "can i use")
    )


def _in_combat_check(message: str, shortcut_id: str | None) -> bool:
    if shortcut_id in COMBAT_SHORTCUTS:
        return True
    lower = message.lower()
    return any(k in lower for k in COMBAT_KEYWORDS)


def detect_dnd_shortcut(message: str, char_dict: dict | None = None) -> str | None:
    lower = message.lower().strip()
    if lower.startswith("/"):
        cmd = lower[1:].split()[0]
        if any(s["id"] == cmd for s in SHORTCUTS):
            return cmd
    if lower.startswith("/cast ") or (lower.startswith("cast ") and " " in lower[5:].strip()):
        return "cast_spell"
    mapping = {
        "ability check": "ability_check",
        "skill check": "ability_check",
        "saving throw": "saving_throw",
        "attack roll": "attack_roll",
        "initiative": "initiative",
        "death save": "death_save",
        "oracle": "oracle",
        "short rest": "short_rest",
        "long rest": "long_rest",
        "rules help": "rules_help",
    }
    for phrase, sid in mapping.items():
        if phrase in lower:
            return sid
    return None


def _parse_cast_spell_name(message: str) -> str:
    text = message.strip()
    lower = text.lower()
    if lower.startswith("/cast "):
        return text[6:].strip()
    if lower.startswith("cast "):
        return text[5:].strip()
    return ""


_CONTINUITY_MECHANICS = (
    " hp",
    "hp ",
    "hit point",
    "damage",
    "falling",
    "prone",
    "unconscious",
    " dies",
    "died",
    "killed",
    "dead",
)


def _needs_continuity_guard(state: DMState) -> bool:
    if is_dice_only_turn(state):
        return False
    task = str((state.get("shortcut_result") or {}).get("task") or "")
    if task in ("short_rest", "long_rest", "cast_spell", "rules_help"):
        return False
    memory = state.get("narrative_context") or {}
    canon = str(memory.get("canon_summary", "") or "")
    recent = str(memory.get("recent_scenes", "") or "")
    if not canon.strip() and not recent.strip():
        return False
    draft = str(state.get("narrative") or state.get("response") or "")
    if not draft.strip():
        return False
    lower = draft.lower()
    if any(sig in lower for sig in _CONTINUITY_MECHANICS):
        return True
    names = re.findall(r"\b[A-Z][a-z]{2,}\b", f"{canon}\n{recent}")
    skip = {"the", "you", "and", "but", "for", "with", "from"}
    return any(name.lower() not in skip and name.lower() in lower for name in names[:40])


def _needs_resource_keeper(state: DMState) -> bool:
    if is_dice_only_turn(state):
        return False
    shortcut = state.get("shortcut_result") or {}
    task = shortcut.get("task")
    if task == "rules_help":
        return False
    if task in ("long_rest", "short_rest") or shortcut.get("pending_rest"):
        return True
    if task == "cast_spell" or shortcut.get("pending_cast"):
        return True
    combined = (
        f"{state.get('user_message', '')}\n{state.get('response') or state.get('narrative') or ''}"
    ).lower()
    return any(sig in combined for sig in _RESOURCE_SIGNALS)


def combat_manager_pre_node(state: DMState) -> DMState:
    session_id = state.get("session_id", "")
    adventure = state.get("adventure") or {}
    adv_id = adventure.get("id", "")
    if not session_id or not adv_id:
        return {}

    combat = load_combat_state(session_id)
    char_dict = state.get("character") or {}
    reaction_events: list[str] = []
    if combat and combat.pending_reaction:
        from backend.games.dnd5e.dm.combat_manager import resolve_pending_reaction, save_combat_state

        combat, char_dict, reaction_events = resolve_pending_reaction(
            combat, char_dict, state.get("user_message") or ""
        )
        save_combat_state(session_id, combat)
    if not combat:
        combat = try_start_planned_encounter(
            session_id,
            adv_id,
            char_dict,
            user_message=state.get("user_message") or "",
            messages=state.get("messages") or [],
        )

    if combat and combat.status == "active":
        from backend.games.dnd5e.dm.combat_manager import save_combat_state, sync_player_combatant

        synced = sync_player_combatant(combat, char_dict)
        if synced != char_dict:
            char_dict = synced
        save_combat_state(session_id, combat)

    updates: DMState = {"in_combat": bool(combat and combat.status == "active")}
    if combat:
        updates["combat_state"] = combat.model_dump()
    if reaction_events:
        updates["combat_events"] = list(state.get("combat_events") or []) + reaction_events
    if char_dict is not state.get("character"):
        updates["character"] = char_dict
        cid = char_dict.get("id")
        if cid:
            from backend.storage import save_character

            save_character(cid, char_dict)
    return updates


def router_node(state: DMState) -> DMState:
    msg = state.get("user_message", "")
    char_dict = state.get("character") or {}
    precomputed = state.get("precomputed_shortcut")
    shortcut = detect_dnd_shortcut(msg, char_dict) if not precomputed else None
    updates: DMState = {
        "needs_rules": _needs_rules_check(msg),
        "in_combat": _in_combat_check(msg, shortcut),
    }
    if precomputed:
        result = precomputed
        updates["shortcut_result"] = result
        updates["mechanics_summary"] = (
            result.get("summary")
            or result.get("user_message")
            or (result.get("dice") or {}).get("summary", "")
        )
        if result.get("entity_updates"):
            updates["character_updates"] = result["entity_updates"]
        task = result.get("task", "")
        if task == "rules_help":
            updates["needs_rules"] = True
        if task in ("ability_check", "saving_throw", "attack_roll", "initiative", "death_save"):
            updates["in_combat"] = _in_combat_check(msg, task)
    elif shortcut:
        char = state.get("character") or {}
        extra: dict = {}
        if shortcut == "cast_spell":
            extra["spell_name"] = _parse_cast_spell_name(msg)
        result = game_plugin(char).run_shortcut(shortcut, **char, **extra)
        updates["shortcut_result"] = result
        updates["mechanics_summary"] = (
            result.get("summary")
            or result.get("user_message")
            or (result.get("dice") or {}).get("summary", "")
        )
        if result.get("entity_updates"):
            updates["character_updates"] = result["entity_updates"]
        if result.get("task") == "rules_help" or shortcut == "rules_help":
            updates["needs_rules"] = True
    return updates


def combat_mechanics_node(state: DMState) -> DMState:
    combat_raw = state.get("combat_state")
    if combat_raw:
        cs = CombatState.model_validate(combat_raw)
        ctx = format_combat_context(cs)
        if ctx:
            return {"combat_context": ctx, "in_combat": True}

    if not state.get("in_combat") and not state.get("shortcut_result"):
        return {"combat_context": ""}
    char_dict = state.get("character") or {}
    char = char_from_dict(char_dict)
    prepared = ", ".join(char.prepared_spells or char.known_spells) or "none"
    reactions = []
    if any(str(s).lower() == "shield" for s in (char.prepared_spells or [])):
        reactions.append("Shield (reaction, +5 AC, 1st-level slot)")
    lines = [
        f"Combat state — {char.name or 'Hero'}: HP {char.hp}/{char.max_hp}, AC {char.ac}",
        f"Spell slots: {char.spell_slots or 'none'}",
        f"Prepared spells: {prepared}",
        f"Prepared reactions: {', '.join(reactions) or 'none'}",
        f"Conditions: {', '.join(char.conditions) if char.conditions else 'none'}",
    ]
    if state.get("mechanics_summary"):
        lines.append(f"Latest roll: {state['mechanics_summary']}")
    task = str((state.get("shortcut_result") or {}).get("task") or "")
    if state.get("in_combat") and task not in ("short_rest", "long_rest", "cast_spell"):
        from backend.games.dnd5e.dm.structured_lookup import (
            format_curated_context,
            lookup_curated_rules,
            rewrite_rules_query,
        )

        combat_query = rewrite_rules_query(state.get("user_message", "") or "")
        curated = lookup_curated_rules(combat_query)
        if curated:
            lines.append(format_curated_context(curated))
    return {"combat_context": "\n".join(lines)}


def rules_referee_node(state: DMState) -> DMState:
    shortcut = state.get("shortcut_result") or {}
    rag_tasks = frozenset({"rules_help"})
    task = shortcut.get("task")
    if task and task not in rag_tasks:
        return {
            "rules_context": shortcut.get("user_message") or shortcut.get("prompt") or "",
            "rules_sources": [],
        }
    if task in rag_tasks:
        msg = shortcut.get("prompt") or state.get("user_message", "")
    elif not state.get("needs_rules"):
        return {"rules_context": "", "rules_sources": []}
    else:
        msg = state.get("user_message", "")
        if state.get("mechanics_summary"):
            msg = f"{msg}\n\nMechanics: {state['mechanics_summary']}"
    include_faerun = bool(state.get("include_faerun", False))
    factions = factions_for(include_faerun, "dnd5e")
    generate = shortcut.get("task") in rag_tasks
    from backend.games.dnd5e.dm.structured_lookup import (
        format_curated_context,
        lookup_curated_rules,
        rewrite_rules_query,
    )
    from backend.settings_store import load_settings

    search_msg = rewrite_rules_query(msg)
    curated = lookup_curated_rules(search_msg)
    curated_block = format_curated_context(curated)
    prefs = load_settings()
    from backend.rag.engine import query_rules

    result = query_rules(
        search_msg,
        game_id="dnd5e",
        factions=factions,
        use_rerank=bool(prefs.get("use_rerank", True)) if generate else False,
        generate_answer=generate,
        character=state.get("character"),
    )
    log_agent(
        "rules_referee",
        "rag_query",
        query=msg[:500],
        source_count=len(result.sources),
        has_answer=bool(result.answer),
    )
    if shortcut.get("task") in rag_tasks and result.answer:
        user_msg = shortcut.get("user_message", "")
        answer = result.answer
        if curated_block:
            answer = f"{curated_block}\n\n{answer}"
        combined = f"{user_msg}\n\n{answer}" if user_msg else answer
        return {
            "rules_context": answer,
            "rules_sources": result.sources,
            "response": combined,
        }
    if not result.sources and not curated_block:
        return {"rules_context": "", "rules_sources": []}
    chunks = []
    if curated_block:
        chunks.append(curated_block)
    for i, src in enumerate(result.sources[:5], 1):
        text = str(src.get("text") or "")
        chunks.append(
            f"[{i}] {src.get('source_label', src.get('label', '?'))} p.{src.get('page', '?')}\n"
            f"{text[:1200]}"
        )
    return {
        "rules_context": "\n\n".join(chunks),
        "rules_sources": result.sources,
    }


def story_director_brief_node(state: DMState) -> DMState:
    task = str((state.get("shortcut_result") or {}).get("task") or "")
    if task in ("rules_help", "short_rest", "long_rest", "cast_spell"):
        return {}
    adventure = state.get("adventure") or {}
    adv_id = adventure.get("id")
    outline = (adventure.get("outline") or "").strip()
    if not adv_id or not outline:
        return {"story_brief": ""}
    progress = ensure_story_progress(adv_id, outline)
    if not progress:
        return {"story_brief": ""}
    return {
        "story_brief": build_narrator_brief(progress),
        "story_progress": progress.model_dump(),
    }


def story_director_update_node(state: DMState) -> DMState:
    if is_dice_only_turn(state):
        return {}
    task = str((state.get("shortcut_result") or {}).get("task") or "")
    if task in ("rules_help", "short_rest", "long_rest", "cast_spell"):
        return {}
    adventure = state.get("adventure") or {}
    adv_id = adventure.get("id")
    if not adv_id:
        return {}
    dm_response = state.get("response") or state.get("narrative") or ""
    if len(dm_response.strip()) < _MIN_RESPONSE_FOR_BOOKKEEPING:
        return {}
    raw = state.get("story_progress")
    if raw:
        from backend.dm.story_director import StoryProgress

        progress = StoryProgress.model_validate(raw)
    else:
        progress = load_story_progress(adv_id)
    if not progress or not progress.checkpoints:
        return {}
    updated = update_progress_after_turn(
        progress,
        user_message=state.get("user_message") or "",
        dm_response=dm_response,
        log_entry=state.get("scribe_log_entry") or "",
    )
    save_story_progress(adv_id, updated)
    completion = apply_completion_if_done(adv_id, updated)
    return {
        "story_progress": updated.model_dump(),
        "adventure_complete": completion.get("adventure_complete", False),
        "next_adventure": completion.get("next_adventure"),
        "player_progress": completion.get("player_progress") or player_progress_view(updated),
    }


def narrator_dm_node(state: DMState) -> DMState:
    shortcut_task = state.get("shortcut_result", {}).get("task")
    if state.get("response") and shortcut_task == "rules_help":
        emit_ready({"response": state["response"]})
        return {"narrative": state["response"], "response": state["response"]}
    pending_updates = dict(state.get("character_updates") or {})
    pending_updates.pop("_logs", None)
    from backend.games.registry import character_dict_for_dm

    char_dict = character_dict_for_dm(state.get("character") or {}, pending_updates=pending_updates)
    char = char_from_dict(char_dict)
    adventure = state.get("adventure") or {}
    include_faerun = bool(state.get("include_faerun", False))
    campaign_id = adventure.get("campaign_id")
    memory = build_narrative_context(adventure, campaign_id, char)
    stable = dnd5e_stable_system_prompt()
    variable = dnd5e_session_context(
        character=char,
        story_brief=state.get("story_brief") or "",
        world_context=memory["world_bible"],
        include_faerun=include_faerun,
    )
    extras = {}
    if state.get("session_id"):
        from backend.storage import get_session

        extras = dict((get_session(state["session_id"]) or {}).get("extras") or {})
    volatile = dnd5e_turn_context(
        character=char,
        canon_summary=memory["canon_summary"],
        recent_scenes=memory["recent_scenes"],
        scene_position=str(extras.get("scene_position") or ""),
    )
    llm = get_langchain_chat_llm("claude")
    user_parts = [state.get("user_message", "")]
    if state.get("mechanics_summary"):
        user_parts.append(f"Mechanical result: {state['mechanics_summary']}")
    if state.get("combat_context"):
        user_parts.append(f"Combat context:\n{state['combat_context']}")
    if state.get("rules_context") and not state.get("response"):
        user_parts.append(f"Relevant rules:\n{state['rules_context']}")
    lc_messages = build_cached_chat_messages(
        stable,
        variable,
        state.get("messages") or [],
        "\n\n".join(user_parts),
        volatile=volatile,
    )
    from backend.games.dnd5e.dm.mechanics_delta import (
        MechanicsStreamFilter,
        apply_mechanics_delta,
        split_mechanics_block,
    )

    delta = None
    if narration_enabled():
        stream_filter = MechanicsStreamFilter(on_text=emit_narration)
        stream_chat_llm(
            llm,
            lc_messages,
            agent="narrator_dm",
            provider="claude",
            on_text=stream_filter.feed,
        )
        text, delta = stream_filter.finish()
    else:
        response = invoke_chat_llm(llm, lc_messages, agent="narrator_dm", provider="claude")
        text, delta = split_mechanics_block(message_text(response))
    text = sanitize_narration_dashes(text.strip())
    if state.get("session_id"):
        from backend.storage import persist_shown_reply

        persist_shown_reply(state["session_id"], state.get("user_message") or "", text)
    ready_payload: dict = {"response": text}
    shortcut = state.get("shortcut_result") or {}
    pending_rest = shortcut.get("pending_rest")
    if not pending_rest:
        task = shortcut.get("task")
        if task in ("short_rest", "long_rest"):
            pending_rest = {"kind": "long" if task == "long_rest" else "short"}
    overlay_preview: dict = {}
    resource_logs: list[str] = []
    try:
        from backend.games.dnd5e.dm.resource_keeper import combat_blocks_rest

        combat_raw = state.get("combat_state")
        combat_active = combat_blocks_rest(combat_state=combat_raw if isinstance(combat_raw, dict) else None)
        overlay_preview, resource_logs = apply_mechanics_delta(
            char_dict,
            delta,
            pending_rest=pending_rest,
            pending_cast=shortcut.get("pending_cast"),
            combat_active=combat_active,
        )
    except Exception:
        overlay_preview, resource_logs = {}, []
    npc_delta = list(overlay_preview.pop("_npcs", []) or [])
    scene_position = str(overlay_preview.pop("_scene_position", "") or "")
    reaction_prompt = overlay_preview.pop("_reaction_prompt", None)
    overlay_preview.pop("_logs", None)
    if pending_updates or overlay_preview:
        preview = dict(char_dict)
        preview.update({k: v for k, v in overlay_preview.items() if not str(k).startswith("_")})
        ready_payload["character"] = preview
        emit_sheet({"character": preview})
    if reaction_prompt:
        ready_payload["reaction_prompt"] = reaction_prompt
    emit_ready(ready_payload)
    scene_updates: DMState = {}
    if state.get("session_id") and scene_position:
        from backend.storage import get_session, update_session_extras

        sess = get_session(state["session_id"]) or {}
        extras = dict(sess.get("extras") or {})
        if scene_position != extras.get("scene_position"):
            extras["scene_position"] = scene_position
            update_session_extras(state["session_id"], extras)
            scene_updates["scene_position"] = scene_position
    result: DMState = {
        "narrative": text,
        "response": text,
        "narrative_context": memory,
        "mechanics_delta": delta.model_dump() if delta else {},
        **scene_updates,
    }
    if overlay_preview:
        merged = dict(pending_updates)
        merged.update(overlay_preview)
        result["character_updates"] = merged
    if resource_logs:
        result["resource_log"] = resource_logs
    result["journal_updates"] = {"npcs": npc_delta, "from_delta": True}
    if reaction_prompt:
        result["reaction_prompt"] = reaction_prompt
    return result


def continuity_guard_node(state: DMState) -> DMState:
    """Kept for tests. Must never rewrite a reply the player already saw."""
    _ = state
    return {}


def resource_keeper_node(state: DMState) -> DMState:
    """Persist the structured delta already applied in the narrator. Do not parse prose."""
    if state.get("character_updates") or state.get("resource_log"):
        return {}
    if state.get("shortcut_result", {}).get("task") == "rules_help":
        return {}
    dm_response = state.get("response") or state.get("narrative") or ""
    from backend.games.dnd5e.dm.mechanics_delta import MechanicsDelta, apply_mechanics_delta, split_mechanics_block

    raw_delta = state.get("mechanics_delta")
    if isinstance(raw_delta, dict) and raw_delta:
        delta = MechanicsDelta.model_validate(raw_delta)
    else:
        _, delta = split_mechanics_block(dm_response)
    shortcut = state.get("shortcut_result") or {}
    pending_rest = shortcut.get("pending_rest")
    task = shortcut.get("task")
    if not pending_rest and task in ("short_rest", "long_rest"):
        pending_rest = {"kind": "long" if task == "long_rest" else "short"}
    combat_raw = state.get("combat_state")
    if not isinstance(combat_raw, dict):
        session_id = state.get("session_id") or ""
        loaded = load_combat_state(session_id) if session_id else None
        combat_raw = loaded.model_dump() if loaded else {}
    from backend.games.dnd5e.dm.resource_keeper import combat_blocks_rest

    updates, logs = apply_mechanics_delta(
        state.get("character") or {},
        delta,
        pending_rest=pending_rest,
        pending_cast=shortcut.get("pending_cast"),
        combat_active=combat_blocks_rest(combat_state=combat_raw),
    )
    updates.pop("_npcs", None)
    updates.pop("_scene_position", None)
    reaction = updates.pop("_reaction_prompt", None)
    updates.pop("_logs", None)
    if not updates and not logs:
        return {}
    result: DMState = {"character_updates": dict(state.get("character_updates") or {})}
    result["character_updates"].update(updates)
    if logs:
        result["resource_log"] = logs
    if reaction:
        result["reaction_prompt"] = reaction
    return result


def combat_manager_post_node(state: DMState) -> DMState:
    if state.get("shortcut_result", {}).get("task") == "rules_help":
        return {}
    session_id = state.get("session_id", "")
    if not session_id:
        return {}
    combat = load_combat_state(session_id)
    if not combat or combat.status != "active":
        return {}

    char_dict = dict(state.get("character") or {})
    before_hp = char_dict.get("hp")
    combat_after, char_dict, events = finish_player_turn(session_id, char_dict)
    result: DMState = {}
    if char_dict != state.get("character") or char_dict.get("hp") != before_hp:
        result["character"] = char_dict
        cid = char_dict.get("id")
        if cid:
            from backend.storage import save_character
            from backend.dm.narration_stream import emit_sheet

            save_character(cid, char_dict)
            emit_sheet({"character": char_dict})
    if events:
        result["combat_events"] = list(state.get("combat_events") or []) + events
    if combat_after:
        view = combat_state_view(
            combat_after if combat_after.status == "active" else load_combat_state(session_id)
        )
        if view:
            result["combat_state"] = view
    return result
