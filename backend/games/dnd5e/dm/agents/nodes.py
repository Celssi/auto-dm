"""D&D 5e DM agent nodes."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.dm.continuity_guard import apply_continuity_guard
from backend.dm.encounters import CombatState, combat_state_view, load_combat_state
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
from backend.games.dnd5e.actions import SHORTCUTS
from backend.games.dnd5e.dm.combat_manager import (
    finish_player_turn,
    format_combat_context,
    player_took_combat_action,
    try_start_planned_encounter,
)
from backend.games.dnd5e.dm.resource_keeper import run_resource_keeper
from backend.llm import get_langchain_chat_llm, invoke_chat_llm
from backend.rag.engine import query_rules
from backend.settings_store import load_settings

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
    "ritual",
)

_MIN_RESPONSE_FOR_BOOKKEEPING = 120


def _needs_rules_check(message: str) -> bool:
    lower = message.lower()
    triggers = [
        "rule",
        "spell",
        "how does",
        "what is",
        "can i",
        "does ",
        "ability",
        "attack",
        "save",
        "rest",
        "level",
        "feat",
        "class feature",
        "monster",
    ]
    return any(t in lower for t in triggers)


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


def _needs_continuity_guard(state: DMState) -> bool:
    memory = state.get("narrative_context") or {}
    if not memory.get("canon_summary", "").strip() and not memory.get("recent_scenes", "").strip():
        return False
    return bool((state.get("narrative") or state.get("response") or "").strip())


def _needs_resource_keeper(state: DMState) -> bool:
    rag_tasks = frozenset({"rules_help"})
    if state.get("shortcut_result", {}).get("task") in (
        *rag_tasks,
        "long_rest",
        "short_rest",
        "cast_spell",
    ):
        return False
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
    if not combat:
        combat = try_start_planned_encounter(
            session_id,
            adv_id,
            state.get("character") or {},
            user_message=state.get("user_message") or "",
            messages=state.get("messages") or [],
        )

    updates: DMState = {"in_combat": bool(combat and combat.status == "active")}
    if combat:
        updates["combat_state"] = combat.model_dump()
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
    lines = [
        f"Combat state — {char.name or 'Hero'}: HP {char.hp}/{char.max_hp}, AC {char.ac}",
        f"Spell slots: {char.spell_slots or 'none'}",
        f"Conditions: {', '.join(char.conditions) if char.conditions else 'none'}",
    ]
    if state.get("mechanics_summary"):
        lines.append(f"Latest roll: {state['mechanics_summary']}")
    if state.get("in_combat"):
        game_id = "dnd5e"
        factions = factions_for(state.get("include_faerun", False), game_id)
        rag = query_rules(
            f"Combat rules for: {state.get('user_message', '')}",
            factions=["player", "monsters"] + (["dm"] if "dm" not in factions else []),
            top_k=3,
            use_rerank=True,
            generate_answer=False,
        )
        if rag.sources:
            lines.append("Combat rules excerpt:")
            for s in rag.sources[:2]:
                lines.append(
                    f"- {s.get('source_label', '?')} "
                    f"p.{s.get('page', '?')}: "
                    f"{s.get('text', '')[:200]}"
                )
    return {"combat_context": "\n".join(lines)}


def rules_referee_node(state: DMState) -> DMState:
    shortcut = state.get("shortcut_result") or {}
    rag_tasks = frozenset({"rules_help"})
    if shortcut.get("task") in rag_tasks:
        msg = shortcut.get("prompt") or state.get("user_message", "")
    elif not state.get("needs_rules") and not shortcut:
        return {"rules_context": "", "rules_sources": []}
    else:
        msg = state.get("user_message", "")
        if state.get("mechanics_summary"):
            msg = f"{msg}\n\nMechanics: {state['mechanics_summary']}"
    prefs = load_settings()
    include_faerun = state.get("include_faerun", False) or prefs.get("include_faerun", False)
    factions = factions_for(include_faerun, "dnd5e")
    generate = shortcut.get("task") in rag_tasks
    result = query_rules(
        msg,
        game_id="dnd5e",
        factions=factions,
        use_rerank=prefs.get("use_rerank", True),
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
        combined = f"{user_msg}\n\n{result.answer}" if user_msg else result.answer
        return {
            "rules_context": result.answer,
            "rules_sources": result.sources,
            "response": combined,
        }
    if not result.sources:
        return {"rules_context": "", "rules_sources": []}
    chunks = []
    for i, src in enumerate(result.sources[:5], 1):
        chunks.append(
            f"[{i}] {src.get('source_label', src.get('label', '?'))} p.{src.get('page', '?')}\n"
            f"{src.get('text', '')[:800]}"
        )
    return {
        "rules_context": "\n\n".join(chunks),
        "rules_sources": result.sources,
    }


def story_director_brief_node(state: DMState) -> DMState:
    if state.get("shortcut_result", {}).get("task") == "rules_help":
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
    if state.get("shortcut_result", {}).get("task") == "rules_help":
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
        return {"narrative": state["response"], "response": state["response"]}
    char_dict = state.get("character") or {}
    char = char_from_dict(char_dict)
    adventure = state.get("adventure") or {}
    prefs = load_settings()
    include_faerun = state.get("include_faerun", False) or prefs.get("include_faerun", False)
    campaign_id = adventure.get("campaign_id")
    memory = build_narrative_context(adventure, campaign_id, char)
    system = game_plugin(char_dict).system_prompt(
        character=char,
        story_brief=state.get("story_brief") or "",
        canon_summary=memory["canon_summary"],
        recent_scenes=memory["recent_scenes"],
        world_context=memory["world_bible"],
        include_faerun=include_faerun,
    )
    llm = get_langchain_chat_llm("claude")
    user_parts = [state.get("user_message", "")]
    if state.get("mechanics_summary"):
        user_parts.append(f"Mechanical result: {state['mechanics_summary']}")
    if state.get("combat_context"):
        user_parts.append(f"Combat context:\n{state['combat_context']}")
    if state.get("rules_context") and not state.get("response"):
        user_parts.append(f"Relevant rules:\n{state['rules_context']}")
    history = state.get("messages") or []
    lc_messages = [SystemMessage(content=system)]
    for m in history[-10:]:
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
    lc_messages.append(HumanMessage(content="\n\n".join(user_parts)))
    response = invoke_chat_llm(llm, lc_messages, agent="narrator_dm", provider="claude")
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = sanitize_narration_dashes(text.strip())
    return {
        "narrative": text,
        "response": text,
        "narrative_context": memory,
    }


def continuity_guard_node(state: DMState) -> DMState:
    if state.get("shortcut_result", {}).get("task") == "rules_help":
        return {}
    if not _needs_continuity_guard(state):
        return {}
    draft = state.get("narrative") or state.get("response") or ""
    if not draft.strip():
        return {}
    memory = state.get("narrative_context") or {}
    final, issues = apply_continuity_guard(
        draft_response=draft,
        user_message=state.get("user_message") or "",
        canon_summary=memory.get("canon_summary", ""),
        world_bible=memory.get("world_bible", ""),
        recent_scenes=memory.get("recent_scenes", ""),
    )
    if issues:
        log_agent("continuity_guard", "revised", issues=issues)
    result: DMState = {"narrative": final, "response": final}
    if issues:
        result["continuity_issues"] = issues
    return result


def resource_keeper_node(state: DMState) -> DMState:
    if not _needs_resource_keeper(state):
        return {}
    shortcut = state.get("shortcut_result") or {}
    task = shortcut.get("task")
    if task in ("rules_help", "long_rest", "short_rest", "cast_spell"):
        return {}
    dm_response = state.get("response") or state.get("narrative") or ""
    if not dm_response.strip():
        return {}
    char_dict = state.get("character") or {}
    updates, logs = run_resource_keeper(
        character=char_dict,
        user_message=state.get("user_message") or "",
        dm_response=dm_response,
    )
    if not updates and not logs:
        return {}
    merged = dict(state.get("character_updates") or {})
    merged.update(updates)
    result: DMState = {"character_updates": merged}
    if logs:
        result["resource_log"] = logs
    return result


def combat_manager_post_node(state: DMState) -> DMState:
    if state.get("shortcut_result", {}).get("task") == "rules_help":
        return {}
    session_id = state.get("session_id", "")
    if not session_id or not load_combat_state(session_id):
        return {}
    if not player_took_combat_action(
        state.get("user_message") or "",
        state.get("shortcut_result"),
    ):
        return {}

    char_dict = state.get("character") or {}
    combat_after, char_dict, events = finish_player_turn(session_id, char_dict)
    result: DMState = {}
    if char_dict != state.get("character"):
        result["character"] = char_dict
    if events:
        result["combat_events"] = events
    if combat_after:
        view = combat_state_view(
            combat_after if combat_after.status == "active" else load_combat_state(session_id)
        )
        if view:
            result["combat_state"] = view
    return result
