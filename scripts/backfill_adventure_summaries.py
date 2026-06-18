#!/usr/bin/env python3
"""Generate adventure/summary.md for adventures that have a log but no summary."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import ANTHROPIC_API_KEY
from backend.dm.story_memory import build_offline_summary, generate_full_summary
from backend.journal_storage import get_campaign
from backend.storage import ADVENTURES_DIR, get_adventure, list_adventures, write_adventure_summary


def main() -> int:
    use_llm = "--local" not in sys.argv and bool(ANTHROPIC_API_KEY)
    if not use_llm:
        print("Using offline summary builder (pass --local explicitly or set ANTHROPIC_API_KEY for LLM).")

    adventures = list_adventures()
    if not adventures:
        print("No adventures found.")
        return 0

    generated = 0
    for row in adventures:
        adv_id = row["id"]
        summary_path = ADVENTURES_DIR / adv_id / "summary.md"
        if summary_path.is_file() and summary_path.read_text(encoding="utf-8").strip():
            print(f"Skip {adv_id}: summary already exists")
            continue

        adventure = get_adventure(adv_id)
        if not adventure:
            continue
        log = adventure.get("log") or ""
        if not log.strip() and not adventure.get("outline"):
            print(f"Skip {adv_id}: no log or outline")
            continue

        story_arc = ""
        campaign_id = adventure.get("campaign_id")
        if campaign_id:
            camp = get_campaign(campaign_id)
            if camp:
                story_arc = camp.get("story_arc") or ""

        if use_llm:
            summary = generate_full_summary(
                log=log,
                outline=adventure.get("outline") or "",
                story_arc=story_arc,
            )
        else:
            summary = build_offline_summary(
                log=log,
                outline=adventure.get("outline") or "",
                story_arc=story_arc,
            )
        write_adventure_summary(adv_id, summary)
        print(f"Generated summary for {adv_id} ({len(summary.splitlines())} lines)")
        generated += 1

    print(f"\nDone. Generated {generated} summary(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
