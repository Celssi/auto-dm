#!/usr/bin/env python3
"""Repair campaign journal and encounters from story arc."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.dm.campaign_repair import repair_campaign


def main() -> None:
    campaign_id = (
        sys.argv[1] if len(sys.argv) > 1 else "the-waking-deep-tides-of-the-shattered-crown"
    )
    result = repair_campaign(
        campaign_id, use_llm=campaign_id != "the-waking-deep-tides-of-the-shattered-crown"
    )
    print(f"Repaired campaign: {campaign_id}")
    print(result)


if __name__ == "__main__":
    main()
