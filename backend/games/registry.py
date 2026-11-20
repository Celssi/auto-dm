"""Game plugin registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException

from backend.games.play_adapter import GamePlayAdapter
from backend.games.rag_hooks import GameRagHooks

DEFAULT_GAME_ID = "dnd5e"

_ALL_PLUGINS: dict[str, "GamePlugin"] | None = None


@dataclass(frozen=True)
class GamePlugin:
    id: str
    label: str
    collection_name: str
    character_from_dict: Callable[..., Any]
    character_to_dict: Callable[..., dict[str, Any]]
    default_character: Callable[[], Any]
    rebuild_character: Callable[..., Any]
    finalize_new_character: Callable[..., Any]
    character_creation_summary: Callable[..., dict[str, Any]]
    character_options_payload: Callable[..., dict[str, Any]]
    shortcuts: list[dict[str, str]]
    run_shortcut: Callable[..., dict[str, Any]]
    match_shortcut: Callable[[str], str | None]
    system_prompt: Callable[..., str]
    get_all_factions: Callable[[], list[str]]
    pdf_sources: dict[str, dict[str, str]]
    format_character_for_prompt: Callable[..., str]
    rag: GameRagHooks
    play: GamePlayAdapter


def resolve_game_id(char_dict: dict[str, Any] | None) -> str:
    if not char_dict:
        return DEFAULT_GAME_ID
    gid = str(char_dict.get("game_id") or DEFAULT_GAME_ID).strip()
    return gid or DEFAULT_GAME_ID


def _load_registry() -> dict[str, GamePlugin]:
    global _ALL_PLUGINS
    if _ALL_PLUGINS is not None:
        return _ALL_PLUGINS
    from backend.games.brambletrek.plugin import BRAMBLETREK_PLUGIN
    from backend.games.dnd5e.plugin import DND5E_PLUGIN

    _ALL_PLUGINS = {DND5E_PLUGIN.id: DND5E_PLUGIN, BRAMBLETREK_PLUGIN.id: BRAMBLETREK_PLUGIN}
    return _ALL_PLUGINS


def get_game(game_id: str | None = None) -> GamePlugin:
    registry = _load_registry()
    gid = (game_id or DEFAULT_GAME_ID).strip() or DEFAULT_GAME_ID
    plugin = registry.get(gid)
    if not plugin:
        raise HTTPException(status_code=400, detail=f"Unknown game: {gid}")
    return plugin


def list_games() -> list[dict[str, str]]:
    return [{"id": g.id, "label": g.label} for g in _load_registry().values()]


def rebuild_character_dict(data: dict[str, Any] | None) -> dict[str, Any]:
    """Recompute derived sheet fields without writing to disk."""
    plugin = get_game(resolve_game_id(data))
    obj = plugin.character_from_dict(data or {})
    rebuilt = plugin.rebuild_character(obj)
    return plugin.character_to_dict(rebuilt)


_RUNTIME_FEATURE_KEYS = (
    "_mage_armor_active",
    "_magic_initiate_free_used",
    "_arcane_recovery_used",
)
_LIVE_RESOURCE_KEYS = (
    "hp",
    "max_hp",
    "spell_slots",
    "hit_dice_spent",
    "hit_dice_max",
    "concentration",
    "luck_points_remaining",
    "second_wind_remaining",
    "lay_on_hands_remaining",
    "wild_shape_uses",
)


def _norm_list(items: Any) -> list[str]:
    return [
        str(item).strip().lower().replace("_", " ")
        for item in (items or [])
        if str(item).strip()
    ]


def _listish_choice_fingerprint(fc: dict[str, Any]) -> dict[str, Any]:
    """Fingerprint list picks so a stringified Python list is persisted as a real list."""
    out: dict[str, Any] = {}
    for key, val in fc.items():
        if str(key).startswith("_"):
            continue
        if isinstance(val, list):
            out[str(key)] = _norm_list(val)
        elif isinstance(val, str) and val.strip().startswith("[") and val.strip().endswith("]"):
            out[str(key)] = val.strip()
    return out


def _migration_fields(data: dict[str, Any] | None) -> dict[str, Any]:
    raw = data or {}
    fc = raw.get("feature_choices") if isinstance(raw.get("feature_choices"), dict) else {}
    return {
        "origin_languages": _norm_list(fc.get("origin_languages")),
        "choice_lists": _listish_choice_fingerprint(fc),
        "elven_lineage": str(fc.get("elven_lineage") or "").strip().lower().replace(" ", "_"),
        "keen_senses_skill": str(fc.get("keen_senses_skill") or "").strip().lower(),
        "high_elf_spell_ability": str(fc.get("high_elf_spell_ability") or "").strip().lower(),
        "magic_initiate_level1": str(fc.get("magic_initiate_level1") or "").strip().lower(),
        "magic_initiate_cantrips": sorted(_norm_list(fc.get("magic_initiate_cantrips"))),
        "magic_initiate_ability": str(fc.get("magic_initiate_ability") or "").strip().lower(),
        "gaming_set_kind": str(fc.get("gaming_set_kind") or "").strip().lower(),
        "spellbook": sorted(_norm_list(raw.get("spellbook"))),
        "languages": sorted(_norm_list(raw.get("languages"))),
        "tool_proficiencies": sorted(_norm_list(raw.get("tool_proficiencies"))),
        "mage_armor": bool(fc.get("_mage_armor_active")),
        "mi_used": bool(fc.get("_magic_initiate_free_used")),
        "hp": int(raw.get("hp") or 0),
        "ac": int(raw.get("ac") or 0),
        "hit_dice_spent": int(raw.get("hit_dice_spent") or 0),
    }


def preserve_live_resources(stored: dict[str, Any] | None, rebuilt: dict[str, Any]) -> dict[str, Any]:
    """Keep in-play HP, slots, HD, and Mage Armor when a 2024 rebuild runs."""
    src = stored or {}
    out = dict(rebuilt)
    for key in _LIVE_RESOURCE_KEYS:
        if key in src and src.get(key) is not None:
            out[key] = src[key]
    stored_fc = src.get("feature_choices") if isinstance(src.get("feature_choices"), dict) else {}
    rebuilt_fc = out.get("feature_choices") if isinstance(out.get("feature_choices"), dict) else {}
    merged_fc = dict(rebuilt_fc)
    for key in _RUNTIME_FEATURE_KEYS:
        if key in stored_fc:
            merged_fc[key] = stored_fc[key]
    out["feature_choices"] = merged_fc
    if resolve_game_id(out) == "dnd5e" and not out.get("ac_manual"):
        from backend.games.dnd5e.characters.entity import character_from_dict
        from backend.games.dnd5e.characters.class_resources import compute_ac_details

        char = character_from_dict(out)
        out["ac"] = int(compute_ac_details(char)["computed"])
        out["hp"] = int(src.get("hp") if src.get("hp") is not None else out.get("hp") or 0)
    return out


def rebuild_character_dict_persisting(
    char_id: str,
    data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Rebuild derived fields and persist 2024 backfills plus live resources when they changed."""
    from backend.storage import save_character

    rebuilt = rebuild_character_dict(data)
    if resolve_game_id(data) != "dnd5e":
        return rebuilt
    merged = preserve_live_resources(data, rebuilt)
    if _migration_fields(data) != _migration_fields(merged):
        save_character(char_id, merged)
        from backend.storage import get_character

        return get_character(char_id) or merged
    return merged
