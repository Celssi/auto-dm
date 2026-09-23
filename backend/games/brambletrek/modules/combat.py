"""Module-specific combat lookups (World Tree guardians, Dragonkeep elementals, Eolan)."""

from __future__ import annotations

from typing import Any

from backend.games.brambletrek.dm.curated import parse_playing_card
from backend.games.brambletrek.modules.combat_data import tactic_band
from backend.games.brambletrek.modules.loader import load_module, module_play_config

GUARDIAN_SUITS = ("hearts", "diamonds")


def module_combat_config(adventure_id: str) -> dict[str, Any]:
    mod = load_module(adventure_id)
    combat = mod.get("combat")
    return dict(combat) if isinstance(combat, dict) else {}


def lookup_guardian(adventure_id: str, card: str) -> dict[str, Any] | None:
    """World Tree: suit + rank → guardian label and health (p. 44)."""
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    suit = parsed["suit"]
    if suit not in GUARDIAN_SUITS:
        return None
    guardians = (module_combat_config(adventure_id).get("guardians") or {}).get(suit) or {}
    row = guardians.get(parsed["rank_key"])
    if not isinstance(row, dict):
        return None
    return {
        "label": row.get("label", ""),
        "health": row.get("health"),
        "card": card,
        "suit": suit,
        "rank_key": parsed["rank_key"],
    }


def resolve_dragonkeep_opponent(gem_path: str, event_card: str) -> str | None:
    parsed = parse_playing_card(event_card)
    if not parsed:
        return None
    by_rank = (module_combat_config("dragonkeep").get("opponent_by_rank") or {}).get(gem_path) or {}
    rk = parsed["rank_key"]
    opp_id = by_rank.get(rk)
    if opp_id:
        return str(opp_id)
    if parsed["rank_key"] in ("jack", "queen", "king"):
        return str(by_rank.get(parsed["rank_key"]) or "")
    return None


def lookup_opponent(adventure_id: str, opponent_id: str) -> dict[str, Any] | None:
    opponents = module_combat_config(adventure_id).get("opponents") or {}
    row = opponents.get(opponent_id)
    return dict(row) if isinstance(row, dict) else None


def lookup_opponent_tactic(
    adventure_id: str,
    opponent_id: str,
    card: str,
) -> dict[str, Any] | None:
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    opponent = lookup_opponent(adventure_id, opponent_id)
    if not opponent:
        return None
    tactics = opponent.get("tactics") or {}
    band = tactic_band(parsed["rank_key"])
    row = tactics.get(band)
    if not isinstance(row, dict):
        return None
    return {"band": band, "card": card, **row}


def lookup_eolan_ally(card: str, phase: str = "1") -> dict[str, Any] | None:
    eolan = module_combat_config("dragonkeep").get("eolan") or {}
    aerith = (eolan.get("aerith_phases") or {}).get(str(phase)) or {}
    tactics = aerith.get("eolan_tactics") or {}
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    band = tactic_band(parsed["rank_key"])
    row = tactics.get(band)
    if not isinstance(row, dict):
        return None
    return {"band": band, "card": card, "phase": phase, **row}


def lookup_aerith_phase_goals(phase: str = "1") -> dict[str, int]:
    eolan = module_combat_config("dragonkeep").get("eolan") or {}
    pdata = (eolan.get("aerith_phases") or {}).get(str(phase)) or {}
    defaults = {"1": (20, 4), "2": (20, 4), "3": (25, 5)}
    dmg_default, rnd_default = defaults.get(str(phase), (20, 4))
    return {
        "damage_goal": int(pdata.get("damage_goal") or dmg_default),
        "rounds_goal": int(pdata.get("rounds_goal") or rnd_default),
        "bands_goal": int(pdata.get("bands_goal") or 7),
    }


def lookup_aerith_tactic(card: str, phase: str = "1") -> dict[str, Any] | None:
    eolan = module_combat_config("dragonkeep").get("eolan") or {}
    aerith = (eolan.get("aerith_phases") or {}).get(str(phase)) or {}
    tactics = aerith.get("aerith_tactics") or {}
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    band = tactic_band(parsed["rank_key"])
    row = tactics.get(band)
    if not isinstance(row, dict):
        return None
    return {"band": band, "card": card, "phase": phase, **row}


def lookup_aerith_item(card: str, phase: str = "1") -> dict[str, Any] | None:
    eolan = module_combat_config("dragonkeep").get("eolan") or {}
    aerith = (eolan.get("aerith_phases") or {}).get(str(phase)) or {}
    items = aerith.get("items") or {}
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    band = tactic_band(parsed["rank_key"])
    row = items.get(band)
    if not isinstance(row, dict):
        return None
    return {"band": band, "card": card, "phase": phase, **row}


def eolan_narrative(step: str) -> str:
    eolan = module_combat_config("dragonkeep").get("eolan") or {}
    block = eolan.get(step) or eolan.get("finale")
    if isinstance(block, dict):
        return str(block.get("body") or "")
    return ""


def format_module_combat_setup(
    cards: list[str],
    *,
    legacy_id: str = "",
    legacy_label: str = "",
    adventure_id: str = "",
    combat_context: dict[str, Any] | None = None,
) -> str:
    """Build combat setup text using module tables when context is available."""
    from backend.games.brambletrek.dm.curated import (
        lookup_player_tactic,
    )

    if len(cards) < 6:
        return ""

    your_init, opp_init = cards[0], cards[1]
    tactic_cards = cards[2:6]
    ctx = combat_context or {}
    adv = adventure_id or str(ctx.get("adventure_id") or "")
    play = module_play_config(adv) if adv else {}

    lines: list[str] = []
    if adv == "world_tree" or ctx.get("type") == "guardian":
        guardian = ctx.get("guardian") if isinstance(ctx.get("guardian"), dict) else None
        if not guardian and ctx.get("card"):
            guardian = lookup_guardian("world_tree", str(ctx["card"]))
        if not guardian:
            guardian = lookup_guardian("world_tree", opp_init)
        if guardian:
            lines.append("**World Tree combat** (guardians, p. 44):")
            lines.append(
                f"- Guardian: **{guardian.get('label', '?')}** — HP {guardian.get('health', '?')} "
                f"({guardian.get('card', opp_init)})."
            )
        else:
            core = lookup_core_opponent(str(ctx.get("card") or opp_init))
            lines.append(
                f"**World Tree combat** (core, clubs/spades) — **{core.get('label', '?')}** (HP {core.get('health', '?')})."
            )
    elif adv == "dragonkeep" or ctx.get("opponent_id"):
        opponent_id = str(ctx.get("opponent_id") or "")
        opponent = lookup_opponent("dragonkeep", opponent_id) if opponent_id else None
        if opponent:
            lines.append(
                f"**Dragonkeep combat** — **{opponent.get('label', opponent_id)}** (HP {opponent.get('health', '?')})."
            )
            if ctx.get("gem_path"):
                lines.append(f"- Path: {str(ctx['gem_path']).replace('_', ' ')}.")
            if ctx.get("event_card"):
                lines.append(f"- Exploration event: {ctx['event_card']}.")
        else:
            lines.append("**Dragonkeep combat** — elemental opponent from your exploration event.")
    elif ctx.get("type") == "core" or play.get("use_core_combat", True):
        core = lookup_core_opponent(str(ctx.get("card") or opp_init))
        lines.append(
            f"**Core combat** (p. 30) — **{core.get('label', 'Opponent')}** (HP {core.get('health', '?')})."
        )
        if adv:
            lines.append(f"- Module: {adv.replace('_', ' ')}.")
    else:
        return ""

    yv = _initiative_value(your_init)
    ov = _initiative_value(opp_init)
    if yv is not None and ov is not None:
        if yv > ov:
            first = "You"
        elif ov > yv:
            first = "Opponent"
        else:
            first = "Tie — redraw or house rule"
        lines.append(
            f"- Initiative: you {your_init} ({yv}) vs opponent {opp_init} ({ov}) — **{first}** goes first."
        )

    opponent_id = str(ctx.get("opponent_id") or "")
    if opponent_id:
        tactic = lookup_opponent_tactic("dragonkeep", opponent_id, opp_init)
        if tactic:
            lines.append(
                f"- Opponent tactic ({tactic.get('band', '?')}): {tactic.get('label', '?')}"
            )
    elif ctx.get("type") == "guardian" or adv == "world_tree":
        lines.append(
            "- Opponent tactics: draw each opponent turn from the module elemental table "
            "(use opponent initiative card band for this round's tactic if house-ruling)."
        )

    leg = legacy_label or legacy_id or "your Legacy"
    lines.append(f"- Your tactic hand ({leg}):")
    for i, card in enumerate(tactic_cards, 1):
        tactic = lookup_player_tactic(legacy_id, card)
        if tactic:
            lines.append(f"  - Tactic {i} ({card}): {tactic['effect']}")
        else:
            lines.append(f"  - Tactic {i} ({card}): set Legacy to resolve tactic table.")

    if opponent_id:
        opponent = lookup_opponent("dragonkeep", opponent_id) or {}
        tactics = opponent.get("tactics") or {}
        if tactics:
            lines.append("")
            lines.append(f"**{opponent.get('label', 'Opponent')} tactics** (curated):")
            for band, meta in tactics.items():
                if isinstance(meta, dict):
                    lines.append(f"- {band}: {meta.get('label', '?')}")

    rules = (module_combat_config("dragonkeep").get("eolan") or {}).get("combat_rules") or {}
    if adv == "dragonkeep" and ctx.get("finale"):
        body = rules.get("body") if isinstance(rules, dict) else ""
        if body:
            lines.append("")
            lines.append(f"**Eolan finale rules:** {body}")

    return "\n".join(lines)


def _initiative_value(card: str) -> int | None:
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    return int(parsed["numeric_value"])


def lookup_core_opponent(card: str) -> dict[str, Any]:
    """Core rulebook opponent type and HP from journey card (p. 30)."""
    from backend.games.brambletrek.dm.curated import _combat_reference

    parsed = parse_playing_card(card)
    if not parsed:
        return {"label": "Opponent", "health": 10, "card": card}
    data = _combat_reference()
    suits = data.get("opponent_type_by_suit") or {}
    hp_map = data.get("opponent_health_by_rank") or {}
    rk = parsed["rank_key"]
    return {
        "label": suits.get(parsed["suit"], "Opponent"),
        "health": int(hp_map.get(rk) or hp_map.get("jack") or 10),
        "card": card,
        "suit": parsed["suit"],
        "rank_key": rk,
    }


def build_combat_context(
    adventure_id: str,
    card: str,
    event: dict[str, Any] | None = None,
    *,
    exploration_table: str = "",
) -> dict[str, Any]:
    """Resolve combat_context for any module journey or exploration row."""
    if exploration_table and adventure_id == "dragonkeep":
        opp_id = resolve_dragonkeep_opponent(exploration_table, card)
        if not opp_id:
            raise ValueError(f"No opponent mapped for {card} on {exploration_table}")
        return {
            "adventure_id": "dragonkeep",
            "gem_path": exploration_table,
            "event_card": card,
            "opponent_id": opp_id,
            "label": (event or {}).get("label", ""),
        }
    if adventure_id == "world_tree":
        guardian = lookup_guardian("world_tree", card)
        if guardian:
            return {
                "adventure_id": "world_tree",
                "type": "guardian",
                "card": card,
                "guardian": guardian,
                "label": guardian.get("label", ""),
            }
        core = lookup_core_opponent(card)
        return {
            "adventure_id": "world_tree",
            "type": "core",
            "card": card,
            "label": core.get("label") or (event or {}).get("label", ""),
            "combat_mode": "core",
        }
    if adventure_id == "birthday_wonders" and event and event.get("combat"):
        return {
            "adventure_id": adventure_id,
            "type": "module",
            "opponent_id": "ratkin_ambush",
            "card": card,
            "label": event.get("label", ""),
        }
    if event and event.get("opponent_id"):
        return {
            "adventure_id": adventure_id,
            "opponent_id": str(event["opponent_id"]),
            "card": card,
            "label": event.get("label", ""),
        }
    play = module_play_config(adventure_id)
    if play.get("use_core_combat", True):
        core = lookup_core_opponent(card)
        return {
            "adventure_id": adventure_id,
            "type": "core",
            "card": card,
            "label": core.get("label") or (event or {}).get("label", ""),
        }
    raise ValueError("Module combat is not configured for this adventure")


def uses_module_combat(adventure_id: str) -> bool:
    if not adventure_id:
        return False
    play = module_play_config(adventure_id)
    if not play.get("use_core_combat", True):
        return True
    return bool(module_combat_config(adventure_id))


def combat_preview_from_context(combat_context: dict[str, Any] | None) -> str:
    if not combat_context:
        return ""
    ctx = combat_context
    if ctx.get("type") == "guardian":
        g = ctx.get("guardian") if isinstance(ctx.get("guardian"), dict) else None
        if g:
            return f"Combat: {g.get('label', '?')} (HP {g.get('health', '?')})"
    if ctx.get("type") == "core":
        core = lookup_core_opponent(str(ctx.get("card") or ""))
        return f"Combat: {core.get('label', 'Opponent')} (HP {core.get('health', '?')})"
    opponent_id = str(ctx.get("opponent_id") or "")
    if opponent_id:
        opp = lookup_opponent(str(ctx.get("adventure_id") or "dragonkeep"), opponent_id)
        if opp:
            return f"Combat: {opp.get('label', opponent_id)} (HP {opp.get('health', '?')})"
    if ctx.get("finale"):
        phase = str(ctx.get("finale_phase") or "1")
        return f"Combat: Aerith (phase {phase})"
    return "Combat pending — use Start combat"
