"""LangGraph DM engine with specialized agent nodes."""

from __future__ import annotations

import re
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from backend.characters.character_builder import (
    character_creation_summary,
    level_up,
    rebuild_character,
)
from backend.characters.entity import character_from_dict, character_to_dict
from backend.characters.spell_resources import is_spell_available
from backend.dm.actions import SHORTCUTS, run_shortcut
from backend.dm.combat_manager import (
    format_combat_context,
    finish_player_turn,
    run_enemy_turns_until_player,
    try_start_planned_encounter,
)
from backend.dm.encounters import combat_state_view, load_combat_state
from backend.dm.continuity_guard import apply_continuity_guard
from backend.dm.journal_keeper import run_journal_keeper
from backend.dm.lonelog import format_mechanical, format_narrative
from backend.dm.narrator import synthesize_lonelog_summary
from backend.dm.prompts import dnd5e_system_prompt
from backend.dm.resource_keeper import run_resource_keeper
from backend.dm.spell_autocomplete import (
    confirmation_message,
    execute_confirmed_cast,
    extract_cast_query,
    is_spell_cancel,
    is_spell_confirmation,
    list_character_spells,
    resolve_spell_query,
)
from backend.dm.story_director import (
    apply_completion_if_done,
    build_narrator_brief,
    ensure_story_progress,
    load_story_progress,
    player_progress_view,
    save_story_progress,
    update_progress_after_turn,
)
from backend.dm.story_memory import build_narrative_context, increment_summary
from backend.dm.trace import dm_turn_trace, log_agent, wrap_node
from backend.llm import ChatProvider, get_langchain_chat_llm, invoke_chat_llm
from backend.rag.engine import query_rules
from backend.rag.plugin import get_all_factions
from backend.settings_store import load_settings
from backend.storage import (
    append_adventure_log,
    append_session_log,
    get_adventure,
    get_character,
    get_session,
    save_character,
    save_session_messages,
    update_session,
    write_adventure_summary,
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
    "ritual",
)


class DMState(TypedDict, total=False):
    session_id: str
    user_message: str
    character: dict
    adventure: dict
    include_faerun: bool
    messages: list[dict]
    in_combat: bool
    needs_rules: bool
    rules_context: str
    rules_sources: list[dict]
    mechanics_summary: str
    combat_context: str
    shortcut_result: dict
    narrative: str
    character_updates: dict
    response: str
    sources: list[dict]
    lonelog_lines: list[str]
    scribe_log_entry: str
    continuity_issues: list[str]
    narrative_context: dict
    resource_log: list[str]
    story_brief: str
    story_progress: dict
    adventure_complete: bool
    next_adventure: dict | None
    player_progress: dict
    combat_state: dict
    combat_events: list[str]


def _factions(include_faerun: bool) -> list[str]:
    if include_faerun:
        return get_all_factions()
    return ["player", "dm", "monsters"]


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


def _detect_shortcut(message: str) -> str | None:
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
    if state.get("shortcut_result", {}).get("task") in (
        "rules_help",
        "long_rest",
        "short_rest",
        "cast_spell",
    ):
        return False
    combined = f"{state.get('user_message', '')}\n{state.get('response') or state.get('narrative') or ''}".lower()
    return any(sig in combined for sig in _RESOURCE_SIGNALS)


def _needs_journal_keeper(state: DMState) -> bool:
    adventure = state.get("adventure") or {}
    if not adventure.get("campaign_id"):
        return False
    dm_response = state.get("response") or state.get("narrative") or ""
    if len(dm_response.strip()) < 80:
        return False
    names = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", dm_response)
    return len(names) >= 2


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
    shortcut = _detect_shortcut(msg)
    updates: DMState = {
        "needs_rules": _needs_rules_check(msg),
        "in_combat": _in_combat_check(msg, shortcut),
    }
    if shortcut:
        char = state.get("character") or {}
        extra: dict = {}
        if shortcut == "cast_spell":
            extra["spell_name"] = _parse_cast_spell_name(msg)
        result = run_shortcut(shortcut, **char, **extra)
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
        from backend.dm.encounters import CombatState

        cs = CombatState.model_validate(combat_raw)
        ctx = format_combat_context(cs)
        if ctx:
            return {"combat_context": ctx, "in_combat": True}

    if not state.get("in_combat") and not state.get("shortcut_result"):
        return {"combat_context": ""}
    char_dict = state.get("character") or {}
    char = character_from_dict(char_dict)
    lines = [
        f"Combat state — {char.name or 'Hero'}: HP {char.hp}/{char.max_hp}, AC {char.ac}",
        f"Spell slots: {char.spell_slots or 'none'}",
        f"Conditions: {', '.join(char.conditions) if char.conditions else 'none'}",
    ]
    if state.get("mechanics_summary"):
        lines.append(f"Latest roll: {state['mechanics_summary']}")
    if state.get("in_combat"):
        factions = _factions(state.get("include_faerun", False))
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
                    f"- {s.get('source_label', '?')} p.{s.get('page', '?')}: {s.get('text', '')[:200]}"
                )
    return {"combat_context": "\n".join(lines)}


def rules_referee_node(state: DMState) -> DMState:
    shortcut = state.get("shortcut_result") or {}
    if shortcut.get("task") == "rules_help":
        msg = shortcut.get("prompt") or state.get("user_message", "")
    elif not state.get("needs_rules") and not shortcut:
        return {"rules_context": "", "rules_sources": []}
    else:
        msg = state.get("user_message", "")
        if state.get("mechanics_summary"):
            msg = f"{msg}\n\nMechanics: {state['mechanics_summary']}"
    prefs = load_settings()
    include_faerun = state.get("include_faerun", False) or prefs.get("include_faerun", False)
    factions = _factions(include_faerun)
    result = query_rules(
        msg,
        factions=factions,
        use_rerank=prefs.get("use_rerank", True),
        generate_answer=shortcut.get("task") == "rules_help",
    )
    log_agent(
        "rules_referee",
        "rag_query",
        query=msg[:500],
        source_count=len(result.sources),
        has_answer=bool(result.answer),
    )
    if shortcut.get("task") == "rules_help" and result.answer:
        return {
            "rules_context": result.answer,
            "rules_sources": result.sources,
            "response": result.answer,
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
    if not dm_response.strip():
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


def narrator_node(state: DMState) -> DMState:
    if state.get("response") and state.get("shortcut_result", {}).get("task") == "rules_help":
        return {"narrative": state["response"], "response": state["response"]}
    char_dict = state.get("character") or {}
    char = character_from_dict(char_dict)
    adventure = state.get("adventure") or {}
    prefs = load_settings()
    include_faerun = state.get("include_faerun", False) or prefs.get("include_faerun", False)
    campaign_id = adventure.get("campaign_id")
    memory = build_narrative_context(adventure, campaign_id, char)
    system = dnd5e_system_prompt(
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
    response = invoke_chat_llm(llm, lc_messages, agent="narrator", provider="claude")
    text = response.content if isinstance(response.content, str) else str(response.content)
    return {
        "narrative": text.strip(),
        "response": text.strip(),
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


def character_keeper_node(state: DMState) -> DMState:
    updates = dict(state.get("character_updates") or {})
    if not updates:
        return {}
    char_dict = dict(state.get("character") or {})
    char_dict.update(updates)
    char = rebuild_character(character_from_dict(char_dict))
    return {"character": character_to_dict(char)}


def scribe_node(state: DMState) -> DMState:
    session_id = state.get("session_id", "")
    narrative = state.get("narrative") or state.get("response", "")
    mechanics = state.get("mechanics_summary", "")
    lines: list[str] = []
    log_entry = ""
    if mechanics:
        lines.append(format_mechanical(mechanics))
    if narrative and state.get("shortcut_result", {}).get("task") != "rules_help":
        summary = synthesize_lonelog_summary(narrative, chat_provider="claude")
        log_entry = summary
        lines.append(format_narrative(summary))
        adventure = state.get("adventure") or {}
        adv_id = adventure.get("id")
        if adv_id:
            append_adventure_log(adv_id, summary)
    for line in lines:
        if session_id:
            append_session_log(session_id, line)
    for resource_line in state.get("resource_log") or []:
        formatted = format_narrative(resource_line)
        if session_id:
            append_session_log(session_id, formatted)
        lines.append(formatted)
    return {"lonelog_lines": lines, "scribe_log_entry": log_entry}


def chronicler_node(state: DMState) -> DMState:
    if state.get("shortcut_result", {}).get("task") == "rules_help":
        return {}
    adventure = state.get("adventure") or {}
    adv_id = adventure.get("id")
    if not adv_id:
        return {}
    dm_response = state.get("response") or state.get("narrative") or ""
    if not dm_response.strip():
        return {}
    existing = adventure.get("summary") or ""
    updated = increment_summary(
        existing,
        user_message=state.get("user_message") or "",
        dm_response=dm_response,
        log_entry=state.get("scribe_log_entry") or "",
    )
    write_adventure_summary(adv_id, updated)
    adventure = dict(adventure)
    adventure["summary"] = updated
    return {"adventure": adventure}


def journal_keeper_node(state: DMState) -> DMState:
    if not _needs_journal_keeper(state):
        return {}
    adventure = state.get("adventure") or {}
    campaign_id = adventure.get("campaign_id")
    adventure_id = adventure.get("id")
    dm_response = state.get("response") or state.get("narrative") or ""
    user_message = state.get("user_message") or ""
    counts = run_journal_keeper(
        campaign_id=campaign_id,
        adventure_id=adventure_id,
        user_message=user_message,
        dm_response=dm_response,
    )
    return {"journal_updates": counts} if counts else {}


def combat_manager_post_node(state: DMState) -> DMState:
    if state.get("shortcut_result", {}).get("task") == "rules_help":
        return {}
    session_id = state.get("session_id", "")
    if not session_id or not load_combat_state(session_id):
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


def build_dm_graph():
    graph = StateGraph(DMState)
    graph.add_node("router", wrap_node("router", router_node))
    graph.add_node("combat_manager_pre", wrap_node("combat_manager_pre", combat_manager_pre_node))
    graph.add_node("combat", wrap_node("combat_mechanics", combat_mechanics_node))
    graph.add_node("rules", wrap_node("rules_referee", rules_referee_node))
    graph.add_node(
        "story_director_brief", wrap_node("story_director_brief", story_director_brief_node)
    )
    graph.add_node("narrator", wrap_node("narrator", narrator_node))
    graph.add_node("continuity_guard", wrap_node("continuity_guard", continuity_guard_node))
    graph.add_node("resource_keeper", wrap_node("resource_keeper", resource_keeper_node))
    graph.add_node("keeper", wrap_node("character_keeper", character_keeper_node))
    graph.add_node("scribe", wrap_node("scribe", scribe_node))
    graph.add_node("chronicler", wrap_node("chronicler", chronicler_node))
    graph.add_node(
        "story_director_update", wrap_node("story_director_update", story_director_update_node)
    )
    graph.add_node("journal_keeper", wrap_node("journal_keeper", journal_keeper_node))
    graph.add_node(
        "combat_manager_post", wrap_node("combat_manager_post", combat_manager_post_node)
    )

    graph.set_entry_point("router")
    graph.add_edge("router", "combat_manager_pre")
    graph.add_edge("combat_manager_pre", "combat")
    graph.add_edge("combat", "rules")
    graph.add_edge("rules", "story_director_brief")
    graph.add_edge("story_director_brief", "narrator")
    graph.add_edge("narrator", "continuity_guard")
    graph.add_edge("continuity_guard", "resource_keeper")
    graph.add_edge("resource_keeper", "keeper")
    graph.add_edge("keeper", "scribe")
    graph.add_edge("scribe", "chronicler")
    graph.add_edge("chronicler", "story_director_update")
    graph.add_edge("story_director_update", "journal_keeper")
    graph.add_edge("journal_keeper", "combat_manager_post")
    graph.add_edge("combat_manager_post", END)
    return graph.compile()


_GRAPH = None


def get_dm_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_dm_graph()
    return _GRAPH


def _finish_early_turn(
    session_id: str,
    messages: list[dict],
    *,
    response: str,
    character: dict,
    character_id: str,
    spell_confirmation: dict | None = None,
    lonelog_lines: list[str] | None = None,
    clear_pending: bool = False,
    persist_character: bool = False,
) -> dict[str, Any]:
    if clear_pending:
        update_session(session_id, {"pending_spell_cast": None})
    messages.append({"role": "assistant", "content": response})
    save_session_messages(session_id, messages)
    for line in lonelog_lines or []:
        append_session_log(session_id, line)
    if persist_character:
        save_character(character_id, character)
    out: dict[str, Any] = {
        "response": response,
        "sources": [],
        "character": character,
        "lonelog_lines": lonelog_lines or [],
    }
    if spell_confirmation:
        out["spell_confirmation"] = spell_confirmation
    return out


def _handle_spell_autocomplete(
    session_id: str,
    user_message: str,
    char: dict,
    messages: list[dict],
) -> dict[str, Any] | None:
    """Intercept fuzzy cast names and pending confirmations before the DM graph."""
    character_id = (get_session(session_id) or {}).get("character_id", "")
    session = get_session(session_id) or {}
    pending = session.get("pending_spell_cast")

    if pending and isinstance(pending, dict):
        spell_name = str(pending.get("spell_name") or pending.get("suggested") or "").strip()
        if is_spell_cancel(user_message):
            return _finish_early_turn(
                session_id,
                messages,
                response=f"Okay, not casting **{spell_name or 'that spell'}**. What do you do instead?",
                character=char,
                character_id=character_id,
                clear_pending=True,
            )
        if is_spell_confirmation(user_message) and spell_name:
            updated_char, response, lonelog = execute_confirmed_cast(
                character_from_dict(char),
                spell_name,
            )
            return _finish_early_turn(
                session_id,
                messages,
                response=response,
                character=updated_char,
                character_id=character_id,
                lonelog_lines=lonelog,
                clear_pending=True,
                persist_character=True,
            )

    query = extract_cast_query(user_message)
    if not query:
        return None

    resolution = resolve_spell_query(character_from_dict(char), query)
    if resolution.status == "exact":
        if pending:
            update_session(session_id, {"pending_spell_cast": None})
        return None

    if resolution.status == "fuzzy":
        update_session(
            session_id,
            {
                "pending_spell_cast": {
                    "requested": resolution.requested,
                    "suggested": resolution.spell_name,
                    "spell_name": resolution.spell_name,
                }
            },
        )
        return _finish_early_turn(
            session_id,
            messages,
            response=confirmation_message(resolution),
            character=char,
            character_id=character_id,
            spell_confirmation={
                "requested": resolution.requested,
                "suggested": resolution.spell_name,
                "spell_name": resolution.spell_name,
            },
        )

    if resolution.status == "unknown" and query:
        available = list_character_spells(character_from_dict(char))
        if available and not is_spell_available(character_from_dict(char), query):
            hint = ", ".join(available[:8])
            return _finish_early_turn(
                session_id,
                messages,
                response=(
                    f'I could not match **"{query}"** to a spell on your sheet. '
                    f"Prepared/known: {hint}{'…' if len(available) > 8 else ''}."
                ),
                character=char,
                character_id=character_id,
                clear_pending=True,
            )
    return None


def run_dm_turn(
    session_id: str,
    user_message: str,
    *,
    chat_provider: ChatProvider = "claude",
) -> dict[str, Any]:
    _ = chat_provider
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")
    char = get_character(session["character_id"]) or {}
    adventure = get_adventure(session["adventure_id"]) or {}
    messages = session.get("messages") or []
    messages.append({"role": "user", "content": user_message})

    early = _handle_spell_autocomplete(session_id, user_message, char, messages)
    if early is not None:
        return early

    adventure = get_adventure(session["adventure_id"]) or {}
    adv_id = adventure.get("id", "")
    character_id = session["character_id"]

    pre_combat_events: list[str] = []
    if adv_id and not load_combat_state(session_id):
        try_start_planned_encounter(
            session_id,
            adv_id,
            char,
            user_message=user_message,
            messages=messages[:-1],
        )

    _, char, pre_combat_events = run_enemy_turns_until_player(session_id, char)
    if char != get_character(character_id):
        save_character(character_id, char)

    prefs = load_settings()
    state: DMState = {
        "session_id": session_id,
        "user_message": user_message,
        "character": char,
        "adventure": adventure,
        "include_faerun": session.get("include_faerun", False)
        or prefs.get("include_faerun", False),
        "messages": messages[:-1],
        "combat_events": pre_combat_events,
    }
    with dm_turn_trace(session_id, user_message):
        result = get_dm_graph().invoke(state)
    response = result.get("response", "")
    post_events = list(result.get("combat_events") or [])
    all_combat_lines = pre_combat_events + post_events
    if all_combat_lines:
        combat_block = "\n\n".join(all_combat_lines)
        response = f"{combat_block}\n\n{response}" if response.strip() else combat_block

    sources = result.get("rules_sources") or []
    updated_char = result.get("character") or char
    if updated_char != char:
        save_character(character_id, updated_char)

    messages.append({"role": "assistant", "content": response})
    save_session_messages(session_id, messages)
    for line in pre_combat_events + post_events:
        append_session_log(session_id, format_mechanical(line))

    combat_view = combat_state_view(load_combat_state(session_id))

    return {
        "response": response,
        "sources": sources,
        "character": updated_char,
        "lonelog_lines": result.get("lonelog_lines") or [],
        "adventure_complete": bool(result.get("adventure_complete")),
        "next_adventure": result.get("next_adventure"),
        "player_progress": result.get("player_progress") or {},
        "combat_state": combat_view,
    }


def level_up_character(
    char_id: str,
    hp_roll: int | None = None,
    class_name: str | None = None,
) -> dict[str, Any]:
    char = get_character(char_id)
    if not char:
        raise ValueError("Character not found")
    obj = level_up(
        rebuild_character(character_from_dict(char)), hp_roll=hp_roll, class_name=class_name
    )
    saved = character_to_dict(obj)
    save_character(char_id, saved)
    return {"character": saved, "summary": character_creation_summary(obj)}
