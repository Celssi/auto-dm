"""D&D 5e LangGraph pipeline."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from backend.dm.nodes.bookkeeping import (
    character_keeper_node,
    chronicler_node,
    journal_keeper_node,
    scribe_node,
)
from backend.dm.state import DMState
from backend.dm.trace import wrap_node
from backend.games.dnd5e.dm.agents import nodes as agents


def build_dnd_graph():
    graph = StateGraph(DMState)
    graph.add_node("router", wrap_node("router", agents.router_node))
    graph.add_node(
        "combat_manager_pre", wrap_node("combat_manager_pre", agents.combat_manager_pre_node)
    )
    graph.add_node("combat", wrap_node("combat_mechanics", agents.combat_mechanics_node))
    graph.add_node("rules", wrap_node("rules_referee", agents.rules_referee_node))
    graph.add_node(
        "story_director_brief", wrap_node("story_director_brief", agents.story_director_brief_node)
    )
    graph.add_node("narrator_dm", wrap_node("narrator_dm", agents.narrator_dm_node))
    graph.add_node("continuity_guard", wrap_node("continuity_guard", agents.continuity_guard_node))
    graph.add_node("resource_keeper", wrap_node("resource_keeper", agents.resource_keeper_node))
    graph.add_node("keeper", wrap_node("character_keeper", character_keeper_node))
    graph.add_node("scribe", wrap_node("scribe", scribe_node))
    graph.add_node("chronicler", wrap_node("chronicler", chronicler_node))
    graph.add_node(
        "story_director_update",
        wrap_node("story_director_update", agents.story_director_update_node),
    )
    graph.add_node("journal_keeper", wrap_node("journal_keeper", journal_keeper_node))
    graph.add_node(
        "combat_manager_post", wrap_node("combat_manager_post", agents.combat_manager_post_node)
    )

    graph.set_entry_point("router")
    graph.add_edge("router", "combat_manager_pre")
    graph.add_edge("combat_manager_pre", "combat")
    graph.add_edge("combat", "rules")
    graph.add_edge("rules", "story_director_brief")
    graph.add_edge("story_director_brief", "narrator_dm")
    graph.add_edge("narrator_dm", "continuity_guard")
    graph.add_edge("continuity_guard", "resource_keeper")
    graph.add_edge("resource_keeper", "keeper")
    graph.add_edge("resource_keeper", "scribe")
    graph.add_edge("scribe", "chronicler")
    graph.add_edge("scribe", "story_director_update")
    graph.add_edge("scribe", "journal_keeper")
    graph.add_edge("keeper", "combat_manager_post")
    graph.add_edge("chronicler", END)
    graph.add_edge("story_director_update", END)
    graph.add_edge("journal_keeper", END)
    graph.add_edge("combat_manager_post", END)
    return graph.compile()
