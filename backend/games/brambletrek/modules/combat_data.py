"""Curated module combat tables (from Complete Digital Edition PDFs)."""

from __future__ import annotations

from typing import Any

TACTIC_BANDS = ("2-4", "5-7", "8-10", "jack", "queen", "king", "ace")


def tactic_band(rank_key: str) -> str:
    if rank_key in ("jack", "queen", "king", "ace"):
        return rank_key
    n = int(rank_key)
    if 2 <= n <= 4:
        return "2-4"
    if 5 <= n <= 7:
        return "5-7"
    return "8-10"


WORLD_TREE_GUARDIANS: dict[str, dict[str, dict[str, Any]]] = {
    "hearts": {
        "2": {"label": "Squirrel Scout", "health": 5},
        "3": {"label": "Forest Fox", "health": 6},
        "4": {"label": "Woodland Deer", "health": 7},
        "5": {"label": "Charging Boar", "health": 8},
        "6": {"label": "Forest Falcon", "health": 9},
        "7": {"label": "Thorned Badger", "health": 10},
        "8": {"label": "Growling Bear", "health": 12},
        "9": {"label": "Soaring Eagle", "health": 13},
        "10": {"label": "Majestic Stag", "health": 14},
        "jack": {"label": "Alpha Wolf", "health": 15},
        "queen": {"label": "Forest Guardian", "health": 17},
        "king": {"label": "King of the Beasts", "health": 20},
        "ace": {"label": "Spirit of the Forest", "health": 25},
    },
    "diamonds": {
        "2": {"label": "Novice Thief", "health": 6},
        "3": {"label": "Travelling Scoundrel", "health": 7},
        "4": {"label": "Ambush Archer", "health": 8},
        "5": {"label": "Dagger Duellist", "health": 9},
        "6": {"label": "Seasoned Marauder", "health": 10},
        "7": {"label": "Battle-hardened Bandit", "health": 11},
        "8": {"label": "Robber Baron", "health": 13},
        "9": {"label": "Armoured Rogue Knight", "health": 14},
        "10": {"label": "Bandit Leader", "health": 15},
        "jack": {"label": "Elite Raider", "health": 16},
        "queen": {"label": "Queen of Thieves", "health": 18},
        "king": {"label": "Bandit King", "health": 21},
        "ace": {"label": "Legendary Outlaw", "health": 26},
    },
}

DRAGONKEEP_OPPONENT_BY_RANK: dict[str, dict[str, str]] = {
    "path_of_tempest": {
        "jack": "water_elemental",
        "queen": "naiad",
        "king": "king_crab",
    },
    "path_of_pyre": {
        "jack": "fire_elemental",
        "queen": "molten_golem",
        "king": "firebird",
    },
    "path_of_leaf": {
        "9": "forest_elemental",
        "jack": "enchanted_treant",
        "queen": "woodland_sprite",
        "king": "forest_wyrm",
    },
}

DRAGONKEEP_OPPONENTS: dict[str, dict[str, Any]] = {
    "water_elemental": {
        "label": "Water Elemental",
        "health": 14,
        "tactics": {
            "2-4": {
                "label": "Soothing Melody: Lowers damage taken by 1 next 3 turns.",
                "opponent_armor": 1,
                "opponent_armor_turns": 3,
            },
            "5-7": {
                "label": "Aqua Dart: Shoots a quick water dart, dealing 2 damage.",
                "damage": 2,
            },
            "8-10": {"label": "Mystic Bubble: Reduces the next damage taken by half (rounded up).", "opponent_halve_next": 1},
            "jack": {
                "label": "Siren's Song: Causes the player to skip their next turn.",
                "skip_turn": True,
            },
            "queen": {"label": "Stream Heal: Restores 4 health points to itself.", "heal": 4},
            "king": {
                "label": "Cascade Strike: A flurry of water strikes, dealing 3 damage.",
                "damage": 3,
            },
            "ace": {
                "label": "Flood Pulse: Deals 5 damage and reduces the player's next attack by 2.",
                "damage": 5,
                "reduce_player_damage": 2,
                "reduce_player_damage_turns": 1,
            },
        },
    },
    "king_crab": {
        "label": "King Crab",
        "health": 16,
        "tactics": {
            "2-4": {"label": "Brackish Snap: Quick pincer attack, dealing 2 damage.", "damage": 2},
            "5-7": {"label": "Shell Guard: Reduces next damage taken by half (rounded up).", "opponent_halve_next": 1},
            "8-10": {"label": "Tidal Pincer: Strong claw attack, dealing 3 damage.", "damage": 3},
            "jack": {
                "label": "Saltwater Spray: Reduces player's attack damage by 3 next turn.",
                "reduce_player_damage": 3,
                "reduce_player_damage_turns": 1,
            },
            "queen": {
                "label": "Dangerous Waters: Deal 2 damage to the player for next 3 turns.",
                "damage": 2,
            },
            "king": {"label": "Crushing Claw: Powerful grip, dealing 4 damage.", "damage": 4},
            "ace": {
                "label": "Ocean's Fury: Ally deals 5 damage; reduce damage taken by 3 next turn.",
                "damage": 5,
            },
        },
    },
    "naiad": {
        "label": "Naiad",
        "health": 12,
        "tactics": {
            "2-4": {"label": "Ripple Strike: Quick water lash, dealing 2 damage.", "damage": 2},
            "5-7": {"label": "Mist Veil: Evades the next attack.", "opponent_evades_next": 1},
            "8-10": {"label": "Surge Blast: Strong water jet, dealing 3 damage.", "damage": 3},
            "jack": {
                "label": "Whirlpool Spin: Reduces player's attack by 1 next turn.",
                "reduce_player_damage": 1,
                "reduce_player_damage_turns": 1,
            },
            "queen": {"label": "Hydro Heal: Restores 2 health points to itself.", "heal": 2},
            "king": {"label": "Tidal Wave: Powerful wave attack, dealing 4 damage.", "damage": 4},
            "ace": {
                "label": "Abyssal Torrent: Deals 5 damage and stuns the player next turn.",
                "damage": 5,
                "skip_turn": True,
            },
        },
    },
    "fire_elemental": {
        "label": "Elemental of Embers",
        "health": 14,
        "tactics": {
            "2-4": {
                "label": "Flame Lash: Strikes with fiery tendrils, dealing 2 damage.",
                "damage": 2,
            },
            "5-7": {
                "label": "Blazing Shield: Reduces damage by 2.",
                "opponent_armor": 2,
                "opponent_armor_turns": 1,
            },
            "8-10": {"label": "Inferno Burst: Fiery explosion, dealing 3 damage.", "damage": 3},
            "jack": {
                "label": "Cinder Dance: Disorients the player, reducing attack by 2 next turn.",
                "reduce_player_damage": 2,
                "reduce_player_damage_turns": 1,
            },
            "queen": {"label": "Flame Renewal: Restores 3 health to itself.", "heal": 3},
            "king": {"label": "Volcanic Strike: Deals 4 damage.", "damage": 4},
            "ace": {
                "label": "Inferno: Deals 5 damage and burns for 2 over next 2 turns.",
                "damage": 5,
            },
        },
    },
    "molten_golem": {
        "label": "Molten Golem",
        "health": 18,
        "tactics": {
            "2-4": {"label": "Lava Throw: Hurls molten rock, dealing 2 damage.", "damage": 2},
            "5-7": {"label": "Rocky Armour: Halves the next attack's damage."},
            "8-10": {
                "label": "Magma Surge: Erupts with molten lava, dealing 3 damage.",
                "damage": 3,
            },
            "jack": {"label": "Quake Stomp: Increase damage dealt by 2 for 2 turns."},
            "queen": {"label": "Regeneration: Heals 2 health per turn for 3 turns.", "heal": 2},
            "king": {"label": "Volcanic Smash: Deals 4 damage.", "damage": 4},
            "ace": {
                "label": "Eruption: Deals 5 damage and stuns the player next turn.",
                "damage": 5,
                "skip_turn": True,
            },
        },
    },
    "firebird": {
        "label": "Firebird",
        "health": 15,
        "tactics": {
            "2-4": {
                "label": "Fiery Plume: Swoops with a fiery attack, dealing 2 damage.",
                "damage": 2,
            },
            "5-7": {"label": "Wing Gust: Reduces the player's attack by 2 until end of turn.", "reduce_player_damage": 2, "reduce_player_damage_turns": 1},
            "8-10": {
                "label": "Blaze Dive: Dives in a ball of fire, dealing 3 damage.",
                "damage": 3,
            },
            "jack": {
                "label": "Rebirth: If defeated, restores half health once (redraw if drawn again)."
            },
            "queen": {"label": "Scorching Cry: Reduces player's defence."},
            "king": {"label": "Solar Flare: Deals 4 damage.", "damage": 4},
            "ace": {
                "label": "Pyre Burst: Deals 5 damage and 1 damage per turn for 2 turns.",
                "damage": 5,
            },
        },
    },
    "forest_elemental": {
        "label": "Forest Elemental",
        "health": 14,
        "tactics": {
            "2-4": {"label": "Barkskin: Reduces incoming damage by 2 for 3 turns.", "opponent_armor": 2, "opponent_armor_turns": 3},
            "5-7": {
                "label": "Root Snare: Reduces player's damage by 2 for 2 turns.",
                "reduce_player_damage": 2,
                "reduce_player_damage_turns": 2,
            },
            "8-10": {"label": "Leafstorm: Whirls leaves to deal 2 damage.", "damage": 2},
            "jack": {
                "label": "Nature's Embrace: Restores 1 health for the next 3 turns.",
                "heal": 1,
            },
            "queen": {"label": "Entangling Vines: Player skips a turn.", "skip_turn": True},
            "king": {"label": "Crushing Limbs: Deals 4 damage.", "damage": 4},
            "ace": {
                "label": "Ancient Growth: Restores 5 health and +4 damage on next tactic.",
                "heal": 5,
            },
        },
    },
    "enchanted_treant": {
        "label": "Enchanted Treant",
        "health": 20,
        "tactics": {
            "2-4": {
                "label": "Branch Whip: Strikes with a long branch, dealing 3 damage.",
                "damage": 3,
            },
            "5-7": {"label": "Sap Coating: Reduces damage taken by 3."},
            "8-10": {"label": "Twig Barrage: 2 damage per turn for 3 turns.", "damage": 2},
            "jack": {"label": "Woodland Stealth: Evades the next tactic card.", "opponent_evades_next": 1},
            "queen": {"label": "Healing Roots: Heals 5 health points.", "heal": 5},
            "king": {
                "label": "Timber Smash: Deals 7 damage to opponent and 4 to itself.",
                "damage": 7,
            },
            "ace": {"label": "Forest's Fury: 2 damage per turn for 2 turns.", "damage": 2},
        },
    },
    "woodland_sprite": {
        "label": "Woodland Sprite",
        "health": 10,
        "tactics": {
            "2-4": {"label": "Sparkle Dust: Player attacks reduced by 2 damage for 3 turns."},
            "5-7": {"label": "Healing Chant: Heals itself by 4.", "heal": 4},
            "8-10": {"label": "Nature's Strike: Deals 4 damage.", "damage": 4},
            "jack": {"label": "Illusion: Player skips their next turn.", "skip_turn": True},
            "queen": {"label": "Wind Dance: Evades the next attack.", "evade": True},
            "king": {"label": "Sprite's Mischief: Steals the last item found by the player."},
            "ace": {
                "label": "Enchanted Whirl: Deals 3 damage; player skips next 2 turns.",
                "damage": 3,
            },
        },
    },
    "forest_wyrm": {
        "label": "Forest Wyrm",
        "health": 18,
        "tactics": {
            "2-4": {"label": "Claw Rake: Deals 3 damage.", "damage": 3},
            "5-7": {"label": "Scale Armour: Halves next damage."},
            "8-10": {"label": "Tail Sweep: Deals 4 damage.", "damage": 4},
            "jack": {"label": "Roar: Player skips next turn.", "skip_turn": True},
            "queen": {"label": "Regenerate: Heals 3 health.", "heal": 3},
            "king": {"label": "Crushing Bite: Deals 5 damage.", "damage": 5},
            "ace": {"label": "Forest Wrath: Deals 6 damage.", "damage": 6},
        },
    },
    "aerith": {
        "label": "Aerith, Keeper of the Moon",
        "health": 60,
        "tactics": {},
    },
    "ratkin_ambush": {
        "label": "Ratkin Ambush",
        "health": 10,
        "tactics": {},
    },
}

DRAGONKEEP_EOLAN: dict[str, Any] = {
    "antechamber": {
        "body": (
            "Eolan tends his wound beside a makeshift camp. Thistle the squirrel watches from his staff. "
            "He seeks the Moon Dragon's treasure and proposes an alliance — together you may reach what "
            "he could not alone."
        ),
    },
    "door": {
        "body": (
            "The Door of Lunar Light bears a cryptic riddle. A slot fits the Oracle's relic; placing it "
            "opens the way to the Deep Chambers."
        ),
        "requires": "oracle_relic",
    },
    "chambers": {
        "body": (
            "Wealth and a chained lunar drake fill the cavern. Aerith descends from the shadows — "
            "the guardian of the smaller drake. Combat with Eolan at your side is inevitable."
        ),
    },
    "combat_rules": {
        "body": (
            "Turn order: Aerith → You → Eolan. Each phase: discard hand and redraw 4 tactic cards. "
            "Survive one of each Aerith attack type to complete a phase (or meet damage goals). "
            "Red Ace/King on Eolan's draw grants Critical Chance (double damage on your next damaging tactic). "
            "Two red face cards in a row completes the phase immediately."
        ),
    },
    "aerith_phases": {
        "1": {
            "label": "Phase 1 — Lunar Fury",
            "goal": "Deal 20 damage to Aerith collectively OR survive 4 rounds.",
            "damage_goal": 20,
            "rounds_goal": 4,
            "bands_goal": 7,
            "aerith_tactics": {
                "2-4": {"label": "Shadow Swipe: Claw strike dealing 2 damage.", "damage": 2},
                "5-7": {
                    "label": "Wing Gust: Reduces your next attack by 1.",
                    "reduce_player_damage": 1,
                    "reduce_player_damage_turns": 1,
                },
                "8-10": {"label": "Tail Whip: Deals 3 damage.", "damage": 3},
                "jack": {"label": "Lunar Roar: You miss your next turn.", "skip_turn": True},
                "queen": {"label": "Darkened Flame: Deals 4 damage.", "damage": 4},
                "king": {
                    "label": "Nightfall Embrace: Your damage reduced by 3 next turn.",
                    "reduce_player_damage": 3,
                    "reduce_player_damage_turns": 1,
                },
                "ace": {
                    "label": "Eclipse Fury: Deals 5 damage; next attack −2.",
                    "damage": 5,
                    "reduce_player_damage": 2,
                    "reduce_player_damage_turns": 1,
                },
            },
            "eolan_tactics": {
                "2-4": {"label": "Quick Shot: Deals 2 damage.", "damage": 2},
                "5-7": {
                    "label": "Defend: Halves Aerith's next attack against you.",
                    "halve_incoming_turns": 1,
                },
                "8-10": {"label": "Strategic Strike: Deals 3 damage.", "damage": 3},
                "jack": {
                    "label": "Coordinated Attack: +2 damage for your next 2 turns.",
                    "damage_bonus": 2,
                    "damage_bonus_turns": 2,
                },
                "queen": {"label": "Healing Herb: Heals you 2 health.", "heal": 2},
                "king": {
                    "label": "Flank Move: Your next attack +3 damage. (CRITICAL)",
                    "critical": True,
                },
                "ace": {
                    "label": "Desperate Blow: Deals 4 damage. (CRITICAL)",
                    "damage": 4,
                    "critical": True,
                },
            },
            "items": {
                "2-4": {
                    "label": "Whispering Wind Chime",
                    "effect": "Reduces Aerith's attack by 1 next turn.",
                    "reduce_opponent_damage": 1,
                },
                "5-7": {
                    "label": "Emberheart Pendant",
                    "effect": "Immunity to fire attacks for two turns.",
                    "halve_incoming_turns": 2,
                },
                "8-10": {
                    "label": "Lunarsteel Blade",
                    "effect": "Deals 3 damage; +1 attack next turn.",
                    "damage": 3,
                },
                "jack": {"label": "Shade Cloak", "effect": "Avoid one Aerith attack.", "evade_next": 1},
                "queen": {"label": "Starlight Elixir", "effect": "Restores 4 health.", "heal": 4},
                "king": {
                    "label": "Dawnbreaker Shield",
                    "effect": "Halves Aerith's next two attacks.",
                    "halve_incoming_turns": 2,
                },
                "ace": {
                    "label": "Phoenix Feather Charm",
                    "effect": "Deals 5 damage; Aerith skips next turn.",
                    "damage": 5,
                    "skip_opponent_turns": 1,
                },
            },
        },
        "2": {
            "label": "Phase 2 — Darkened Assault",
            "goal": "Deal 20 damage OR survive 4 rounds.",
            "damage_goal": 20,
            "rounds_goal": 4,
            "bands_goal": 7,
            "aerith_tactics": {
                "2-4": {"label": "Darkened Talons: 3 damage for two turns.", "damage": 3},
                "5-7": {
                    "label": "Shadow Breath: Reduces your attack by 2 next turn.",
                    "reduce_player_damage": 2,
                    "reduce_player_damage_turns": 1,
                },
                "8-10": {"label": "Lunar Strike: Deals 4 damage.", "damage": 4},
                "jack": {"label": "Eclipse Swoop: You miss your next turn.", "skip_turn": True},
                "queen": {"label": "Nightshade Flames: Deals 5 damage.", "damage": 5},
                "king": {
                    "label": "Veil of Darkness: Your attacks miss for 2 turns.",
                    "player_attacks_miss_turns": 2,
                },
                "ace": {"label": "Fury of the Night Sky: Deals 6 damage.", "damage": 6},
            },
            "eolan_tactics": {
                "2-4": {"label": "Arrow of Light: Deals 3 damage.", "damage": 3},
                "5-7": {
                    "label": "Shield of Valour: Halves Aerith's next attack.",
                    "halve_incoming_turns": 1,
                },
                "8-10": {"label": "Warrior's Finesse: Deals 4 damage.", "damage": 4},
                "jack": {
                    "label": "Duo Assault: +2 damage on your next attack.",
                    "damage_bonus": 2,
                    "damage_bonus_turns": 1,
                },
                "queen": {"label": "Herbal Remedy: Heals you 3 health.", "heal": 3},
                "king": {
                    "label": "Tactical Retreat: +4 damage on your next attack. (CRITICAL)",
                    "critical": True,
                },
                "ace": {
                    "label": "Heroic Charge: Deals 5 damage. (CRITICAL)",
                    "damage": 5,
                    "critical": True,
                },
            },
            "items": {
                "2-4": {"label": "Starlit Sash", "effect": "+1 attack for two turns.", "damage_bonus": 1, "damage_bonus_turns": 2},
                "5-7": {"label": "Ember of Courage", "effect": "Nullifies Aerith's next attack.", "evade_next": 1},
                "8-10": {"label": "Moonbeam Flask", "effect": "Restores 5 health.", "heal": 5},
                "jack": {"label": "Twilight Dagger", "effect": "Deals 4 damage; Aerith −3 next attack.", "damage": 4, "reduce_opponent_damage": 3},
                "queen": {"label": "Shield of Dawn", "effect": "Halves Aerith's next three attacks.", "halve_incoming_turns": 3},
                "king": {"label": "Comet's Heart", "effect": "Deals 6 damage; stuns Aerith.", "damage": 6, "skip_opponent_turns": 1},
                "ace": {"label": "Eclipse Orb", "effect": "Deals 7 damage; +3 on your next attack.", "damage": 7, "damage_bonus": 3, "damage_bonus_turns": 1},
            },
        },
        "3": {
            "label": "Phase 3 — Cosmic Wrath",
            "goal": "Deal 25 damage OR survive 5 rounds.",
            "damage_goal": 25,
            "rounds_goal": 5,
            "bands_goal": 7,
            "aerith_tactics": {
                "2-4": {"label": "Nightmare Claws: Deals 4 damage.", "damage": 4},
                "5-7": {
                    "label": "Shadow Maelstrom: Your attack −3 next turn.",
                    "reduce_player_damage": 3,
                    "reduce_player_damage_turns": 1,
                },
                "8-10": {"label": "Lunar Fury: Deals 5 damage.", "damage": 5},
                "jack": {"label": "Dread Dive: You lose your next turn.", "skip_turn": True},
                "queen": {"label": "Dark Nova: Deals 6 damage.", "damage": 6},
                "king": {
                    "label": "Eclipse's Embrace: Your damage −3 for 3 turns.",
                    "reduce_player_damage": 3,
                    "reduce_player_damage_turns": 3,
                },
                "ace": {"label": "Cosmic Wrath: Deals 7 damage.", "damage": 7},
            },
            "eolan_tactics": {
                "2-4": {"label": "Light of Hope: Deals 4 damage.", "damage": 4},
                "5-7": {
                    "label": "Guardian's Shield: Reflects Aerith's next attack.",
                    "reflect_next": 1,
                },
                "8-10": {"label": "Final Strike: Deals 5 damage.", "damage": 5},
                "jack": {
                    "label": "United Front: +3 damage on your next attack.",
                    "damage_bonus": 3,
                    "damage_bonus_turns": 1,
                },
                "queen": {
                    "label": "Lifespring Herb: Regain 4 health per turn for 2 turns.",
                    "heal": 4,
                    "heal_per_turn_turns": 2,
                },
                "king": {
                    "label": "Daring Feint: 6 damage to Eolan, 3 to you. (CRITICAL)",
                    "damage": 6,
                    "self_damage": 3,
                    "critical": True,
                },
                "ace": {
                    "label": "Valiant Rush: Deals 6 damage. (CRITICAL)",
                    "damage": 6,
                    "critical": True,
                },
            },
            "items": {
                "2-4": {"label": "Gleaming Star Orb", "effect": "+2 attack next turn.", "damage_bonus": 2, "damage_bonus_turns": 1},
                "5-7": {"label": "Mantle of Shadows", "effect": "Avoid Aerith's next attack.", "evade_next": 1},
                "8-10": {"label": "Flameheart Talisman", "effect": "Deals 4 damage; fire ward 2 turns.", "damage": 4, "halve_incoming_turns": 2},
                "jack": {"label": "Lunar Shard", "effect": "Aerith's next two attacks −5.", "reduce_opponent_damage": 5, "reduce_opponent_damage_turns": 2},
                "queen": {"label": "Eclipse Arrow", "effect": "Deals 5 damage; Aerith −1 attack.", "damage": 5, "reduce_opponent_damage": 1},
                "king": {"label": "Duskblade Dagger", "effect": "Deals 6 damage; dodge one attack.", "damage": 6, "evade_next": 1},
                "ace": {"label": "Celestial Shield", "effect": "Deals 7 damage; halves next attack.", "damage": 7, "halve_incoming_turns": 1},
            },
        },
    },
    "finale": {
        "body": (
            "After Aerith falls, the lunar drake awakens. The key clatters down. Eolan asks whether "
            "to free the drake or claim the treasure — the key shatters after one use. There is no "
            "wrong answer; you exit via a secret door to the forest."
        ),
    },
}


def world_tree_combat_section() -> dict[str, Any]:
    return {"guardians": WORLD_TREE_GUARDIANS}


def dragonkeep_combat_section() -> dict[str, Any]:
    return {
        "opponent_by_rank": DRAGONKEEP_OPPONENT_BY_RANK,
        "opponents": DRAGONKEEP_OPPONENTS,
        "eolan": DRAGONKEEP_EOLAN,
    }
