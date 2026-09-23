"""Brambletrek DM agent nodes."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.dm.prose_style import sanitize_narration_dashes
from backend.dm.state import DMState, char_from_dict, game_plugin
from backend.dm.trace import log_agent
from backend.llm import get_langchain_chat_llm, invoke_chat_llm
from backend.rag.engine import query_rules
from backend.settings_store import load_settings
from backend.storage import get_session

RAG_DIRECT_TASKS = frozenset({"rag_direct"})


def detect_brambletrek_shortcut(message: str, char_dict: dict | None = None) -> str | None:
    plugin = game_plugin(char_dict)
    active = str((char_dict or {}).get("active_adventure") or "")
    matched = plugin.match_shortcut(message)
    if matched:
        return matched
    if message.strip().lower() in {"/day", "/journey"}:
        return "adventure_scene" if active else "journey_day"
    return None


def router_node(state: DMState) -> DMState:
    msg = state.get("user_message", "")
    char_dict = state.get("character") or {}
    precomputed = state.get("precomputed_shortcut")
    shortcut = detect_brambletrek_shortcut(msg, char_dict) if not precomputed else None
    updates: DMState = {"needs_rules": False, "in_combat": False}
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
        if result.get("task") in RAG_DIRECT_TASKS:
            updates["needs_rules"] = True
    elif shortcut:
        char = state.get("character") or {}
        sess = get_session(state.get("session_id", "")) or {}
        extras = sess.get("extras") or {}
        extra = {
            "card_source": extras.get("card_source", "virtual"),
            "story_mode": extras.get("story_mode", "player"),
        }
        result = game_plugin(char).run_shortcut(shortcut, **char, **extra)
        updates["shortcut_result"] = result
        updates["mechanics_summary"] = (
            result.get("summary")
            or result.get("user_message")
            or (result.get("dice") or {}).get("summary", "")
        )
        if result.get("entity_updates"):
            updates["character_updates"] = result["entity_updates"]
        if result.get("task") in RAG_DIRECT_TASKS:
            updates["needs_rules"] = True
        if result.get("journey_cards") and state.get("session_id"):
            from backend.games.brambletrek.play_handlers import stash_pending_journey

            stash_pending_journey(
                state["session_id"],
                str(char.get("id") or ""),
                result,
                result.get("journey_shortcut_id") or shortcut or "journey_day",
            )
    return updates


def rules_facilitator_node(state: DMState) -> DMState:
    shortcut = state.get("shortcut_result") or {}
    if shortcut.get("task") in RAG_DIRECT_TASKS:
        msg = shortcut.get("prompt") or state.get("user_message", "")
    elif not state.get("needs_rules") and not shortcut:
        return {"rules_context": "", "rules_sources": []}
    else:
        msg = state.get("user_message", "")
        if state.get("mechanics_summary"):
            msg = f"{msg}\n\nMechanics: {state['mechanics_summary']}"
    prefs = load_settings()
    result = query_rules(
        msg,
        game_id="brambletrek",
        factions=game_plugin(state.get("character")).get_all_factions(),
        use_rerank=prefs.get("use_rerank", True),
        generate_answer=shortcut.get("task") in RAG_DIRECT_TASKS,
        character=state.get("character"),
    )
    log_agent(
        "rules_facilitator",
        "rag_query",
        query=msg[:500],
        source_count=len(result.sources),
        has_answer=bool(result.answer),
    )
    if shortcut.get("task") in RAG_DIRECT_TASKS and result.answer:
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


def _should_run_facilitator(state: DMState) -> bool:
    shortcut_task = (state.get("shortcut_result") or {}).get("task")
    if state.get("response") and shortcut_task in RAG_DIRECT_TASKS:
        return False
    if shortcut_task in RAG_DIRECT_TASKS:
        return False
    sess = get_session(state.get("session_id", "")) or {}
    story_mode = (sess.get("extras") or {}).get("story_mode", "player")
    return story_mode == "ai_narrator"


def facilitator_node(state: DMState) -> DMState:
    if not _should_run_facilitator(state):
        shortcut_task = (state.get("shortcut_result") or {}).get("task")
        if state.get("response") and shortcut_task in RAG_DIRECT_TASKS:
            return {"narrative": state["response"], "response": state["response"]}
        return {}
    char_dict = state.get("character") or {}
    char = char_from_dict(char_dict)
    sess = get_session(state.get("session_id", "")) or {}
    extras = sess.get("extras") or {}
    system = game_plugin(char_dict).system_prompt(
        character=char,
        story_mode=extras.get("story_mode", "player"),
        card_source=extras.get("card_source", "virtual"),
    )
    llm = get_langchain_chat_llm("claude")
    user_parts = [state.get("user_message", "")]
    if state.get("mechanics_summary"):
        user_parts.append(f"Mechanical result: {state['mechanics_summary']}")
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
    response = invoke_chat_llm(llm, lc_messages, agent="facilitator", provider="claude")
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = sanitize_narration_dashes(text.strip())
    return {
        "narrative": text,
        "response": text,
    }
