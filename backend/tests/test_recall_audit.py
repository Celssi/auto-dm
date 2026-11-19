from backend.rag.recall_audit import score_sources


def test_score_sources_hits_on_title():
    sources = [
        {
            "section_title": "Exhaustion",
            "text": "The target has a penalty.",
            "printed_page": "366",
        }
    ]
    scored = score_sources(
        sources,
        {
            "id": "exhaustion-what",
            "expect_title": "Exhaustion",
            "expect_terms": ["d20", "speed"],
            "printed_page": 366,
        },
    )
    assert scored["hit"] is True
    assert scored["title_hit"] is True
    assert scored["terms_hit"] is False
    assert scored["page_hit"] is True


def test_score_sources_hits_on_all_terms():
    sources = [
        {
            "section_title": "Mastery Properties",
            "text": "Cleave: extra melee attack once per turn.",
            "printed_page": "214",
        }
    ]
    scored = score_sources(
        sources,
        {
            "id": "mastery-cleave",
            "expect_title": "Cleave",
            "expect_terms": ["melee", "once per turn"],
            "printed_page": 214,
        },
    )
    assert scored["hit"] is True
    assert scored["terms_hit"] is True


def test_score_sources_miss_without_title_or_terms():
    sources = [{"section_title": "Unrelated", "text": "Something else", "printed_page": "10"}]
    scored = score_sources(
        sources,
        {
            "id": "heroic-inspiration",
            "expect_title": "Heroic Inspiration",
            "expect_terms": ["reroll"],
            "printed_page": 13,
        },
    )
    assert scored["hit"] is False
    assert scored["page_hit"] is False
