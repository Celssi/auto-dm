"""Background diff normalization tests."""

from __future__ import annotations

from backend.characters.background_extract import BackgroundSpec, diff_background


def test_diff_tool_ignores_choose_one_kind_prefix():
    spec = BackgroundSpec(
        id="artisan",
        label="Artisan",
        tool="Artisan's Tools",
    )
    extracted = {"tool": "Choose one kind of Artisan's Tools", "feat": "Crafter"}
    assert diff_background(spec, extracted) == []


def test_diff_feat_ignores_see_chapter_suffix():
    spec = BackgroundSpec(
        id="harper",
        label="Harper Agent",
        feat="Harper Agent",
        skills=["performance", "sleight_of_hand"],
        tool="Disguise Kit",
    )
    extracted = {
        "feat": "Harper Agent (see “Feats” later in this chapter)",
        "skills": ["performance", "sleight_of_hand"],
        "tool": "Disguise Kit",
    }
    assert diff_background(spec, extracted) == []
