"""Tests for per-game compiled agent pipelines."""

from __future__ import annotations

from backend.dm.graph_factory import get_dm_graph, reset_dm_graphs


def _node_names(game_id: str) -> set[str]:
    reset_dm_graphs()
    graph = get_dm_graph(game_id)
    nodes = graph.get_graph().nodes
    return {n for n in nodes if n not in ("__start__", "__end__")}


def test_dnd_graph_has_combat_and_narrator_dm():
    names = _node_names("dnd5e")
    assert "combat_manager_pre" in names
    assert "narrator_dm" in names
    assert "story_director_brief" in names
    assert "continuity_guard" in names
    assert "resource_keeper" in names


def test_brambletrek_graph_has_facilitator_not_combat():
    names = _node_names("brambletrek")
    assert "rules" in names or "rules_facilitator" in names
    assert "facilitator" in names
    assert "combat_manager_pre" not in names
    assert "narrator_dm" not in names
    assert "story_director_brief" not in names
    assert "continuity_guard" not in names
    assert "resource_keeper" not in names


def test_both_graphs_share_bookkeeping():
    for game_id in ("dnd5e", "brambletrek"):
        names = _node_names(game_id)
        assert "keeper" in names
        assert "scribe" in names
