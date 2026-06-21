"""Structured session audit log for rules forensics."""

from __future__ import annotations

from typing import Any

from backend.dm.trace import get_turn_context
from backend.storage import append_session_audit, get_session_audit

_AUDIT_SLICE_KEYS = (
    "hp",
    "max_hp",
    "spell_slots",
    "concentration",
    "death_save_successes",
    "death_save_failures",
    "exhaustion",
    "wild_shape_uses",
    "hit_dice_spent",
    "conditions",
)


def character_audit_slice(char: dict[str, Any] | None) -> dict[str, Any]:
    if not char:
        return {}
    out: dict[str, Any] = {}
    for key in _AUDIT_SLICE_KEYS:
        if key not in char:
            continue
        val = char.get(key)
        if key == "spell_slots" and isinstance(val, dict):
            out[key] = {str(k): int(v or 0) for k, v in val.items()}
        elif key == "conditions" and isinstance(val, list):
            out[key] = list(val)
        else:
            out[key] = val
    return out


def diff_character_slices(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    keys = set(before) | set(after)
    for key in keys:
        if before.get(key) != after.get(key):
            diff[key] = {"before": before.get(key), "after": after.get(key)}
    return diff


def audit_context() -> dict[str, str]:
    ctx = get_turn_context()
    if not ctx:
        return {}
    return dict(ctx)


def record_audit(
    event: dict[str, Any],
    *,
    session_id: str | None = None,
) -> None:
    """Append one structured audit event to the session audit log."""
    if "event" not in event:
        return
    sid = session_id or event.get("session_id") or audit_context().get("session_id") or ""
    if not sid:
        return
    ctx = audit_context()
    payload: dict[str, Any] = {
        "session_id": sid,
        **event,
    }
    if ctx.get("turn_id") and "turn_id" not in payload:
        payload["turn_id"] = ctx["turn_id"]
    append_session_audit(sid, payload)


def read_audit_events(session_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
    return get_session_audit(session_id, limit=limit)


def format_audit_summary(event: dict[str, Any]) -> str:
    """One-line human summary for UI."""
    etype = str(event.get("event") or "")
    detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
    before = event.get("before") if isinstance(event.get("before"), dict) else {}
    after = event.get("after") if isinstance(event.get("after"), dict) else {}

    if etype == "dice_roll":
        total = detail.get("total")
        notation = detail.get("notation", "")
        return f"{notation} = {total}" if total is not None else str(notation)

    if etype == "hp_change":
        b = before.get("hp", detail.get("hp_before"))
        a = after.get("hp", detail.get("hp_after"))
        dmg = detail.get("damage")
        if dmg is not None:
            return f"HP {b}→{a} (−{dmg})"
        return f"HP {b}→{a}"

    if etype == "spell_slot":
        lvl = detail.get("slot_level", "?")
        b = before.get("spell_slots", {})
        a = after.get("spell_slots", {})
        if isinstance(b, dict) and isinstance(a, dict):
            bs = b.get(str(lvl), b.get(lvl))
            asn = a.get(str(lvl), a.get(lvl))
            return f"L{lvl} slot {bs}→{asn}"
        return f"Spent L{lvl} slot"

    if etype == "spell_cast":
        spell = detail.get("spell", "?")
        ritual = detail.get("ritual")
        if ritual:
            return f"Ritual {spell}"
        return f"Cast {spell}"

    if etype == "rest":
        kind = detail.get("kind", "rest")
        return str(kind).replace("_", " ").title()

    if etype == "combat_attack":
        hit = detail.get("hit")
        dmg = detail.get("damage", 0)
        attacker = detail.get("attacker", "?")
        if hit:
            return f"{attacker} hit for {dmg}"
        return f"{attacker} miss"

    if etype == "combat_start":
        name = detail.get("encounter_name", "Combat")
        return f"Started: {name}"

    if etype == "concentration":
        maintained = detail.get("maintained")
        spell = detail.get("spell", "")
        return f"Concentration {'kept' if maintained else 'lost'} ({spell})"

    if etype == "death_save":
        roll = detail.get("roll")
        succ = after.get("death_save_successes", detail.get("successes"))
        fail = after.get("death_save_failures", detail.get("failures"))
        return f"Death save {roll} ({succ}S/{fail}F)"

    if etype == "character_patch":
        diff = event.get("diff") if isinstance(event.get("diff"), dict) else {}
        if diff:
            parts = [f"{k}" for k in list(diff.keys())[:3]]
            return f"Updated: {', '.join(parts)}"
        return "Character updated"

    if etype == "oracle":
        return str(detail.get("summary", "Oracle roll"))

    if etype == "wild_shape":
        uses = after.get("wild_shape_uses", detail.get("uses"))
        mx = detail.get("max")
        return f"Wild Shape {uses}/{mx}"

    return etype.replace("_", " ")
