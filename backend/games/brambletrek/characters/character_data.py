"""Brambletrek character options for API."""

from __future__ import annotations

from typing import Any

from backend.games.brambletrek.characters.entity import (
    get_legacy_options,
    load_character_tables,
    table_options,
)
from backend.games.brambletrek.dm.curated import (
    _legacies_data,
    adventure_options,
    legacy_abilities,
    overcome_the_odds,
)


def character_options_payload(**_kwargs) -> dict[str, Any]:
    legacies = []
    for lid, data in get_legacy_options().items():
        if not lid:
            continue
        raw = (_legacies_data().get("legacies") or {}).get(lid) or {}
        legacies.append(
            {
                "id": lid,
                "label": data["label"],
                "boost": data.get("boost"),
                "flaw": data.get("flaw"),
                "health_delta": int(raw.get("health_delta", 0) or 0),
                "morale_delta": int(raw.get("morale_delta", 0) or 0),
                "supplies_delta": int(raw.get("supplies_delta", 0) or 0),
                "abilities": [
                    {
                        "id": ab["id"],
                        "label": ab["label"],
                        "description": ab.get("description", ""),
                        "tags": ab.get("tags") or [],
                    }
                    for ab in legacy_abilities(lid)
                ],
            }
        )
    oto = overcome_the_odds()
    adventures_meta = []
    from backend.games.brambletrek.dm.curated import adventure_meta

    for adv_id, label in adventure_options():
        meta = adventure_meta(adv_id)
        adventures_meta.append(
            {
                "id": adv_id,
                "label": label,
                "synopsis": meta.get("synopsis", ""),
                "tips": meta.get("tips") or [],
                "acts": meta.get("acts") or [],
            }
        )
    return {
        "reasons": [{"id": o[0], "label": o[1]} for o in table_options("reasons")],
        "backgrounds": [{"id": o[0], "label": o[1]} for o in table_options("backgrounds")],
        "trinkets": [{"id": o[0], "label": o[1]} for o in table_options("trinkets")],
        "card_bands": [
            {"id": str(row.get("id", "")), "label": str(row.get("label", ""))}
            for row in (load_character_tables().get("card_bands") or [])
            if isinstance(row, dict) and row.get("id")
        ],
        "legacies": legacies,
        "adventures": adventures_meta,
        "overcome_the_odds": oto,
    }
