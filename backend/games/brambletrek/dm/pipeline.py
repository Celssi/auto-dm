"""Brambletrek LangGraph pipeline."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from backend.dm.nodes.bookkeeping import character_keeper_node, scribe_node
from backend.dm.state import DMState
from backend.dm.trace import wrap_node
from backend.games.brambletrek.dm.agents import nodes as agents


def resolve_response_node(state: DMState) -> DMState:
    """Player mode: use shortcut/mechanics output when facilitator is skipped."""
    if state.get("response"):
        return {}
    parts: list[str] = []
    if state.get("mechanics_summary"):
        parts.append(state["mechanics_summary"])
    shortcut = state.get("shortcut_result") or {}
    if shortcut.get("user_message"):
        parts.append(shortcut["user_message"])
    if not parts:
        return {}
    text = "\n\n".join(parts)
    return {"response": text, "narrative": text}


def build_brambletrek_graph():
    graph = StateGraph(DMState)
    graph.add_node("router", wrap_node("router", agents.router_node))
    graph.add_node("rules", wrap_node("rules_facilitator", agents.rules_facilitator_node))
    graph.add_node("resolve", wrap_node("resolve_response", resolve_response_node))
    graph.add_node("facilitator", wrap_node("facilitator", agents.facilitator_node))
    graph.add_node("keeper", wrap_node("character_keeper", character_keeper_node))
    graph.add_node("scribe", wrap_node("scribe", scribe_node))

    graph.set_entry_point("router")
    graph.add_edge("router", "rules")
    graph.add_edge("rules", "resolve")
    graph.add_edge("resolve", "facilitator")
    graph.add_edge("facilitator", "keeper")
    graph.add_edge("keeper", "scribe")
    graph.add_edge("scribe", END)
    return graph.compile()
