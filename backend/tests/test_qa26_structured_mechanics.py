"""QA of Paladin playthrough #25: structured mechanics deltas, not narrative regex."""

from backend.dm.memory_dedupe import looks_like_entity_name
from backend.games.dnd5e.characters.class_resources import weapon_attack_details
from backend.games.dnd5e.characters.entity import character_from_dict
from backend.games.dnd5e.dm.mechanics_delta import (
    MECHANICS_START,
    MechanicsDelta,
    MechanicsStreamFilter,
    apply_mechanics_delta,
    parse_mechanics_delta,
    render_mechanics_block,
    split_mechanics_block,
)
from backend.games.dnd5e.dm.resource_keeper import apply_pending_rest, overlay_live_resources
from backend.dm.journal_keeper import apply_npc_delta


def _paladin(**overrides):
    data = {
        "id": "paladin-qa",
        "name": "QA Paladin",
        "species": "human",
        "class_name": "paladin",
        "level": 1,
        "hp": 12,
        "max_hp": 12,
        "ac": 18,
        "hit_die": 10,
        "hit_dice_max": 1,
        "hit_dice_spent": 0,
        "lay_on_hands_remaining": 0,
        "heroic_inspiration": False,
        "conditions": [],
        "active_effects": [],
        "concentration": "Bless",
        "spell_slots": {"1": 1},
        "classes": [{"class_name": "paladin", "level": 1}],
        "inventory": ["chalk", "button"],
        "currency": {"gp": 23, "cp": 7},
        "ability_scores": {"str": 16, "dex": 10, "con": 14, "int": 8, "wis": 10, "cha": 15},
        "weapons": [
            {"name": "Longsword", "damage": "1d8", "damage_type": "slashing", "ability": "str"},
            {"name": "Shortbow", "damage": "1d6", "damage_type": "piercing", "ability": "str"},
        ],
    }
    data.update(overrides)
    return data


def _narration(prose: str, **delta) -> str:
    return f"{prose}\n{render_mechanics_block(delta)}"


def test_prose_without_delta_does_not_change_hp():
    text = "The ghost drains you for 7 damage. HP 12 -> 5/12."
    overlay = overlay_live_resources(_paladin(), text)
    assert overlay.get("hp") is None
    assert "Took" not in " ".join(overlay.get("_logs") or [])


def test_hp_delta_applies_damage_and_logs_source():
    updates, logs = apply_mechanics_delta(
        _paladin(),
        MechanicsDelta.model_validate({"hp_changes": [{"amount": -7, "source": "ghost"}]}),
    )
    assert updates["hp"] == 5
    assert any("Took 7 damage (ghost)" in line for line in logs)


def test_trap_damage_delta():
    updates, logs = apply_mechanics_delta(
        _paladin(),
        {"hp_changes": [{"amount": -5, "source": "trap"}]},
    )
    assert updates["hp"] == 7
    assert any("trap" in line for line in logs)


def test_split_strips_fence_from_visible_text():
    prose = "The trap snaps shut."
    visible, delta = split_mechanics_block(_narration(prose, hp_changes=[{"amount": -5, "source": "trap"}]))
    assert visible == prose
    assert MECHANICS_START not in visible
    assert delta.hp_changes[0].amount == -5


def test_stream_filter_hides_partial_fence():
    filt = MechanicsStreamFilter()
    filt.feed("The ghost howls. <<<MECH")
    filt.feed("ANICS\n{\"hp_changes\":[{\"amount\":-7,\"source\":\"ghost\"}]}\n>>>")
    visible, delta = filt.finish()
    assert "ghost howls" in visible
    assert "hp_changes" not in visible
    assert delta.hp_changes[0].amount == -7


def test_long_rest_restores_lay_on_hands():
    updates, logs = apply_mechanics_delta(
        _paladin(lay_on_hands_remaining=0, hp=5),
        {"rest": {"kind": "long"}},
    )
    assert updates["lay_on_hands_remaining"] == 5
    assert updates["hp"] == 12
    assert any("Long rest" in line for line in logs)


def test_recap_loh_without_delta_does_not_spend():
    overlay = overlay_live_resources(
        _paladin(lay_on_hands_remaining=5),
        "Earlier you used Lay on Hands 5 -> 0. The pool is empty.",
    )
    assert overlay.get("lay_on_hands_remaining") is None


def test_concentration_end_clears_bless():
    updates, logs = apply_mechanics_delta(
        _paladin(concentration="Bless"),
        {"concentration": {"action": "end"}},
    )
    assert updates["concentration"] == ""
    assert any("Concentration ended" in line for line in logs)


def test_interrupted_rest_is_short_not_long():
    char = _paladin(hp=5, lay_on_hands_remaining=0, hit_dice_spent=0)
    updates, logs = apply_pending_rest(
        char,
        {"kind": "long"},
        _narration("The rest is interrupted. You only get a short rest.", rest={"kind": "interrupted"}),
    )
    assert updates.get("hp") in (None, 5) or updates["hp"] < 12
    assert updates.get("lay_on_hands_remaining") in (None, 0)
    assert any("Interrupted rest" in line or "Short rest" in line for line in logs)


def test_pending_long_rest_without_delta_is_not_applied():
    updates, logs = apply_pending_rest(
        _paladin(hp=5),
        {"kind": "long"},
        "You settle in for the night, then goblins kick the door. The rest is interrupted.",
    )
    assert updates == {}
    assert any("did not grant a rest" in line for line in logs)


def test_refused_rest_from_delta():
    updates, logs = apply_pending_rest(
        _paladin(),
        {"kind": "short"},
        _narration("No time to rest.", refused=["rest"]),
    )
    assert updates == {}
    assert any("refused" in line.lower() for line in logs)


def test_npc_delta_skips_rules_terms():
    assert looks_like_entity_name("Bless") is False
    assert looks_like_entity_name("Savage Attacker") is False
    assert looks_like_entity_name("Disadvantage") is False
    assert looks_like_entity_name("Grab Bettany") is False
    assert looks_like_entity_name("Snag") is True
    updates = apply_npc_delta(
        "camp",
        [
            {"name": "Bless", "action": "introduce"},
            {"name": "Snag", "action": "introduce", "note": "Goblin lookout"},
        ],
    )
    assert [item.name for item in updates.new_npcs] == ["Snag"]


def test_frightened_dc_only_when_condition_added():
    updates, logs = apply_mechanics_delta(
        _paladin(),
        {
            "conditions": [
                {"name": "Frightened", "action": "add", "save_dc": 13, "source": "ghost"},
            ]
        },
    )
    assert updates["conditions"] == ["Frightened"]
    effects = updates["active_effects"]
    assert effects[0]["save_dc"] == 13
    assert any("Frightened save DC 13" in line for line in logs)


def test_succeeded_save_does_not_add_frightened():
    updates, _ = apply_mechanics_delta(
        _paladin(),
        {"hp_changes": [], "conditions": []},
    )
    assert "conditions" not in updates


def test_heroic_inspiration_grant_and_spend():
    granted, logs = apply_mechanics_delta(_paladin(), {"resources": {"heroic_inspiration": "grant"}})
    assert granted["heroic_inspiration"] is True
    spent, logs2 = apply_mechanics_delta(
        {**_paladin(), "heroic_inspiration": True},
        {"resources": {"heroic_inspiration": "spend"}},
    )
    assert spent["heroic_inspiration"] is False
    assert any("granted" in line.lower() for line in logs)
    assert any("spent" in line.lower() for line in logs2)


def test_shortbow_attack_uses_dex():
    rows = weapon_attack_details(character_from_dict(_paladin()))
    by_name = {row["name"]: row for row in rows}
    assert by_name["Shortbow"]["ability"] == "dex"
    assert by_name["Shortbow"]["attack"] == 2
    assert by_name["Longsword"]["attack"] == 5


def test_reaction_prompt_is_not_auto_resolved():
    updates, _ = apply_mechanics_delta(
        _paladin(),
        {
            "reaction_prompt": {
                "kind": "opportunity_attack",
                "prompt": "The goblin leaves your reach. Use your reaction to attack?",
                "target": "goblin",
            }
        },
    )
    assert updates["_reaction_prompt"]["kind"] == "opportunity_attack"
    assert updates.get("hp") is None


def test_parse_rejects_garbage():
    assert parse_mechanics_delta("not json") == MechanicsDelta()
    assert parse_mechanics_delta("") == MechanicsDelta()


def test_coins_and_items_delta():
    updates, logs = apply_mechanics_delta(
        _paladin(),
        {
            "coins": {"gp": 5, "cp": -2},
            "items": {"add": ["silver key"], "remove": ["chalk"]},
        },
    )
    assert updates["currency"]["gp"] == 28
    assert updates["currency"]["cp"] == 5
    assert "silver key" in updates["inventory"]
    assert "chalk" not in updates["inventory"]
    assert any("Gained silver key" in line for line in logs)
    assert any("Lost chalk" in line for line in logs)


def test_empty_npc_delta_does_not_extract_from_prose():
    from backend.dm.nodes.bookkeeping import journal_keeper_node

    result = journal_keeper_node(
        {
            "adventure": {"campaign_id": "camp", "id": "adv"},
            "response": "You cast Bless. Savage Attacker waits. Disadvantage hangs in the air.",
            "journal_updates": {"npcs": [], "from_delta": True},
            "character": _paladin(),
        }
    )
    assert result == {}


def test_concentration_start_sets_spell():
    updates, logs = apply_mechanics_delta(
        _paladin(concentration=""),
        {"concentration": {"action": "start", "spell": "Bless"}},
    )
    assert updates["concentration"] == "Bless"
    assert any("Concentration: Bless" in line for line in logs)
