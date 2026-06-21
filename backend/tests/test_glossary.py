from backend.glossary import build_glossary_index, lookup_entry


def test_dungeoneers_pack_uses_curated_item_not_rag_index():
    hit = lookup_entry("Dungeoneer's Pack", use_rag=True)
    assert hit["kind"] == "item"
    assert hit["title"] == "Dungeoneer's Pack"
    summary = hit["summary"] or ""
    assert "Backpack" in summary
    assert "crowbar" in summary
    assert "Drawmij" not in summary
    assert "Druid class" not in summary


def test_javelins_lookup_is_weapon_not_shield_spell():
    hit = lookup_entry("Javelins (8)", use_rag=True)
    assert hit["kind"] == "weapon"
    summary = hit["summary"] or ""
    assert "Shield" not in summary
    assert "Abjuration" not in summary
    assert "Javelin" in hit["title"] or "javelin" in summary.lower()


def test_flail_lookup_is_weapon():
    hit = lookup_entry("flail", use_rag=True)
    assert hit["kind"] == "weapon"
    assert "Flail" in hit["title"]
    assert "1d8" in (hit["summary"] or "")


def test_common_packs_indexed():
    index = build_glossary_index()
    for key in ("dungeoneerspack", "explorerspack", "priestspack", "scholarspack"):
        assert index[key]["kind"] == "item"
        assert index[key]["summary"]
