"""NPC/location memory merges stay readable and skip action prompts as names."""

from __future__ import annotations

from backend.dm.memory_dedupe import (
    condense_body,
    looks_like_entity_name,
    merge_update,
)


def test_merge_update_skips_restated_facts():
    body = (
        "Dalla is a fisherwoman. She confessed to poisoning the harbor, causing the fish die-off."
    )
    assert (
        merge_update(body, "Dalla confessed she poisoned the harbor and caused the fish die-off.")
        is None
    )


def test_merge_update_appends_only_new_sentences():
    body = "Mira is a scout for the guild."
    merged = merge_update(
        body, "Mira is a scout for the guild. Mira betrayed the guild to the Red Hand."
    )
    assert merged is not None
    assert merged.count("[Update]") == 1
    assert merged.endswith("Mira betrayed the guild to the Red Hand.")


def test_condense_body_drops_duplicate_update_paragraphs():
    body = (
        "Dalla runs the smokehouse.\n\n[Update]\nDalla and Larry now trust each other."
        "\n\n[Update]\nDalla and Larry now trust each other completely."
        "\n\n[Update]\nDalla agreed to guide Larry to the sea cave."
    )
    out = condense_body(body)
    assert out.count("[Update]") == 2
    assert "sea cave" in out


def test_entity_name_filter():
    assert looks_like_entity_name("Dalla")
    assert looks_like_entity_name("Captain Mirel of the Tide")
    assert looks_like_entity_name("Salthollow Harbor")
    assert not looks_like_entity_name("Ask Dalla to come with you")
    assert not looks_like_entity_name("Search the docks")
    assert not looks_like_entity_name("What now?")


def test_apply_journal_updates_dedupes_and_filters(isolated_saves):
    from backend import journal_storage
    from backend.dm.journal_keeper import (
        JournalEntryUpdate,
        JournalTurnUpdates,
        apply_journal_updates,
    )

    journal_storage.save_campaign("camp", {"name": "Camp", "character_ids": []})
    journal_storage.save_campaign_npc(
        "camp", None, {"name": "Dalla", "body": "Dalla confessed to poisoning the harbor."}
    )
    updates = JournalTurnUpdates(
        new_npcs=[
            JournalEntryUpdate(name="Ask Dalla to come with you", body="Option."),
            JournalEntryUpdate(name="Dalla", body="Dalla agreed to guide Larry to the sea cave."),
        ],
        updated_npcs=[
            JournalEntryUpdate(name="dalla", body="Dalla confessed poisoning the harbor.")
        ],
    )
    counts = apply_journal_updates(campaign_id="camp", adventure_id=None, updates=updates)
    npcs = journal_storage.list_campaign_npcs("camp")
    assert [n["name"] for n in npcs] == ["Dalla"]
    body = journal_storage.get_campaign_npc("camp", npcs[0]["id"])["body"]
    assert body.count("[Update]") == 1
    assert "sea cave" in body
    assert counts["new_npcs"] == 0
    assert counts["updated_npcs"] == 1
