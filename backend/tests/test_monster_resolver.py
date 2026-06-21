"""Monster resolver tests with mocked RAG."""

from unittest.mock import MagicMock, patch

from backend.games.dnd5e.dm.monster_resolver import MonsterAttack, MonsterStats, lookup_monster


def test_lookup_monster_uses_llm_parsed_stats():
    lookup_monster.cache_clear()
    rag_result = MagicMock()
    rag_result.sources = [{"source_label": "MM", "page": "220", "text": "Merrow AC 13 HP 45"}]
    parsed = MonsterStats(
        name="Merrow",
        ac=13,
        hp=45,
        attacks=[MonsterAttack(name="Harpoon", to_hit=6, damage="2d6+3")],
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = parsed

    llm_path = "backend.games.dnd5e.dm.monster_resolver.get_langchain_chat_llm"
    with patch("backend.games.dnd5e.dm.monster_resolver.query_rules", return_value=rag_result):
        with patch(llm_path, return_value=mock_llm):
            stats = lookup_monster("Merrow")

    assert stats.name == "Merrow"
    assert stats.ac == 13
    assert stats.hp == 45
    assert stats.attacks[0].damage == "2d6+3"


def test_lookup_monster_fallback_when_no_rag():
    lookup_monster.cache_clear()
    rag_result = MagicMock()
    rag_result.sources = []

    with patch("backend.games.dnd5e.dm.monster_resolver.query_rules", return_value=rag_result):
        stats = lookup_monster("Unknown Beast")

    assert stats.name == "Unknown Beast"
    assert stats.ac == 12
    assert stats.hp == 22
    assert stats.attacks
