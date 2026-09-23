"""Brambletrek sidebar shortcuts: prompts and pre-drawn deck results."""

from __future__ import annotations

from typing import Literal, TypedDict

from backend.games.brambletrek.characters.entity import get_legacy_options, label_for_band
from backend.games.brambletrek.dm.curated import (
    adventure_meta,
    adventure_options,
    combat_reference_summary,
    format_adventure_context,
    format_combat_setup_curated,
    format_journey_events,
    format_reason_ending,
    format_recovery_draw,
    legacy_by_roll,
    legacy_id_by_roll,
)
from backend.games.brambletrek.modules.loader import (
    format_adventure_scene,
    journey_cards_for_adventure,
    module_exploration_tables,
    module_has_curated_tables,
    module_journey_tables,
    module_play_config,
    module_scene_tables,
)
from backend.play_tools import draw_cards, format_card_result, format_dice_result, roll_dice

GAME_BRAMBLETREK = "brambletrek"


def _adventure_draw_plan(active_adventure: str) -> tuple[int, bool, str]:
    """Return route card count, whether activity cards follow, and exploration table id."""
    if not active_adventure:
        return 4, False, ""
    if module_scene_tables(active_adventure).get("choose_adventure"):
        return 3, True, ""
    exploration = module_exploration_tables(active_adventure)
    table_id = str(module_play_config(active_adventure).get("default_scene_table") or "")
    if table_id and exploration.get(table_id):
        return (
            int(module_play_config(active_adventure).get("journey_cards_per_day") or 3),
            False,
            table_id,
        )
    if module_journey_tables(active_adventure):
        return journey_cards_for_adventure(active_adventure), False, ""
    return 4, False, ""


ShortcutKind = Literal["card_rag", "multi_draw_rag", "roll_rag", "rag_only", "static"]

MULTI_DRAW_SHORTCUTS = frozenset(
    {
        "journey_day",
        "aldwund_day",
        "adventure_scene",
        "combat_setup",
        "resources",
        "random_character",
        "overcome_odds",
    }
)


class BrambletrekShortcut(TypedDict):
    id: str
    label: str
    kind: ShortcutKind


def _wants_core_journey(text: str) -> bool:
    """Explicit Hyhill / core journey table intent (not adventure-module scenes)."""
    lower = text.lower()
    return any(
        p in lower
        for p in (
            "hyhill",
            "surface journey",
            "core journey",
            "journey & exploration",
            "journey and exploration",
            "page 24",
            "page 25",
            "page 26",
            "page 27",
            "aldwund",
            "depths day",
            "depths of aldwund",
        )
    )


def match_brambletrek_shortcut(text: str, *, active_adventure: str = "") -> str | None:
    """Map natural-language Brambletrek requests to sidebar shortcut ids."""
    lower = text.lower().strip()

    adventure_scene_phrases = (
        "adventure scene",
        "next scene",
        "scene card",
        "module scene",
        "pumpkin hunt",
        "festival activity",
        "choose your adventure",
    )
    if active_adventure and any(p in lower for p in adventure_scene_phrases):
        return "adventure_scene"

    journey_phrases = (
        "journey day",
        "exploration day",
        "today's journey",
        "todays journey",
        "this day's journey",
        "daily journey",
        "cards for today",
        "meanings for today",
        "for today",
        "start my journey",
        "start the journey",
        "begin my journey",
        # colloquial — still matches everyday play
        "day one",
        "day 1",
        "first day",
        "cards for day",
        "meanings for day",
        "for day one",
        "for day 1",
    )
    aldwund_phrases = (
        "aldwund day",
        "aldwund journey",
        "depths day",
        "in the depths",
        "depths of aldwund",
        "exploring the depths",
    )
    if any(p in lower for p in aldwund_phrases):
        return "aldwund_day"
    if _wants_core_journey(lower) and any(w in lower for w in ("journey", "exploration")):
        return "journey_day"
    if active_adventure and not _wants_core_journey(lower):
        if any(p in lower for p in journey_phrases):
            return "adventure_scene"
        if ("character ready" in lower or "character is ready" in lower) and any(
            w in lower for w in ("play", "start", "cards", "meaning", "today", "day")
        ):
            return "adventure_scene"
        if any(w in lower for w in ("draw", "give me", "cards")) and any(
            w in lower for w in ("scene", "act", "today", "day")
        ):
            return "adventure_scene"
    if any(p in lower for p in journey_phrases):
        return "journey_day"
    if ("character ready" in lower or "character is ready" in lower) and any(
        w in lower for w in ("journey", "play", "start", "exploration", "meaning", "today", "day")
    ):
        return "journey_day"
    if any(w in lower for w in ("journey", "exploration")) and any(
        w in lower for w in ("draw", "give me", "cards", "four", "4 card")
    ):
        if active_adventure and not _wants_core_journey(lower):
            return "adventure_scene"
        return "journey_day"

    if any(p in lower for p in ("combat setup", "start combat", "initiative and tactic")):
        return "combat_setup"
    if "overcome the odds" in lower or ("ability" in lower and "outcome" in lower):
        return "overcome_odds"
    if "random character" in lower or "random gnawborn" in lower:
        return "random_character"
    if any(
        p in lower for p in ("how do i start", "how to start playing", "how do i play brambletrek")
    ):
        return "start_playing"
    if any(
        p in lower
        for p in (
            "story ending",
            "reason ending",
            "end my story",
            "end my journey",
            "how does my story end",
            "finish my journey",
            "page 36",
        )
    ):
        return "reason_ending"
    if any(
        p in lower
        for p in (
            "adventure overview",
            "active adventure",
            "about this adventure",
            "adventure module",
        )
    ):
        return "adventure_overview"

    return None


BRAMBLETREK_SHORTCUTS: list[BrambletrekShortcut] = [
    {"id": "start_playing", "label": "How to start playing", "kind": "rag_only"},
    {"id": "journey_day", "label": "Journey day (4 cards)", "kind": "multi_draw_rag"},
    {"id": "aldwund_day", "label": "Aldwund day (4 cards)", "kind": "multi_draw_rag"},
    {"id": "random_character", "label": "Random character", "kind": "multi_draw_rag"},
    {"id": "reason", "label": "Reason for adventure", "kind": "card_rag"},
    {"id": "background", "label": "Background", "kind": "card_rag"},
    {"id": "trinket", "label": "Trinket", "kind": "card_rag"},
    {"id": "resources", "label": "Resources (6 cards)", "kind": "multi_draw_rag"},
    {"id": "combat_setup", "label": "Combat setup", "kind": "multi_draw_rag"},
    {"id": "overcome_odds", "label": "Overcome the odds", "kind": "multi_draw_rag"},
    {"id": "recovery_health", "label": "Health recovery", "kind": "card_rag"},
    {"id": "recovery_morale", "label": "Morale recovery", "kind": "card_rag"},
    {"id": "recovery_supplies", "label": "Supplies recovery", "kind": "card_rag"},
    {"id": "random_legacy", "label": "Random Legacy (d6)", "kind": "roll_rag"},
    {"id": "legacy_overview", "label": "Legacy overview", "kind": "rag_only"},
    {"id": "reason_ending", "label": "Reason ending (p. 36)", "kind": "rag_only"},
    {"id": "adventure_overview", "label": "Active adventure overview", "kind": "rag_only"},
    {"id": "adventure_scene", "label": "Adventure scene (3 cards)", "kind": "multi_draw_rag"},
]


def _adventure_select_help(*, for_scene: bool = False) -> str:
    intro = (
        "**Adventure scene** — pick an active adventure first."
        if for_scene
        else "**Active adventure** — choose a module for your campaign."
    )
    lines = [
        intro,
        "",
        "In the app: **Settings** (gear icon) → **Character** → **Active adventure** → **Save character setup**.",
        "",
        "Available modules:",
    ]
    for aid, label in adventure_options():
        if aid:
            lines.append(f"- **{label}**")
    lines.extend(
        [
            "- **Hyhill solo (core rules)** — leave Active adventure empty for standard forest play.",
            "",
            "After selecting a module, use **Adventure scene (3 cards)** in Play → Shortcuts, "
            "or **Journey day** for core Hyhill tables.",
        ]
    )
    return "\n".join(lines)


def shortcuts_for_character(*, active_adventure: str = "") -> list[BrambletrekShortcut]:
    """Sidebar shortcuts; adventure scene only when a module is selected."""
    out: list[BrambletrekShortcut] = []
    for shortcut in BRAMBLETREK_SHORTCUTS:
        if shortcut["id"] == "adventure_scene" and not active_adventure:
            continue
        item: BrambletrekShortcut = dict(shortcut)
        if (
            active_adventure
            and item["id"] == "journey_day"
            and module_has_curated_tables(active_adventure)
        ):
            n, paired, _ = _adventure_draw_plan(active_adventure)
            adv = adventure_meta(active_adventure)
            suffix = f" — {adv.get('label', active_adventure)}"
            if paired:
                item["label"] = f"Adventure activities ({n}×2 cards){suffix}"
            else:
                item["label"] = f"Journey day ({n} cards){suffix}"
        out.append(item)
    return out


_CARD_RAG_PROMPTS: dict[str, str] = {
    "reason": (
        "Draw for my reason for adventure and explain it from the Reason for Adventure "
        "table (Core Rulebook page 12)."
    ),
    "background": (
        "Draw for my Background and explain it from the Background table (Core Rulebook page 13)."
    ),
    "trinket": (
        "Draw for my Trinket and explain it from the Trinket table (Core Rulebook page 14)."
    ),
}


class ShortcutRun(TypedDict, total=False):
    user_message: str
    prompt: str
    kind: ShortcutKind
    journey_cards: list[str]


def _draw_lines(
    game_id: str,
    count: int,
    labels: list[str] | None = None,
    *,
    char_id: str | None = None,
    card_source: str = "virtual",
) -> tuple[list[str], str]:
    if card_source == "physical":
        label_list = labels or [f"Draw {i + 1}" for i in range(count)]
        lines = "\n".join(f"- **{label}:** _(physical deck)_" for label in label_list)
        msg = (
            f"**Physical deck mode** — draw **{count}** card(s) from your real deck, "
            "report each via sidebar **Record card** or chat (e.g. *Queen of Hearts*), "
            f"then re-run this shortcut or ask for meanings.\n\n{lines}"
        )
        return [], msg

    result = draw_cards(count=count, game_id=game_id, char_id=char_id)
    if not result.get("ok"):
        summary = format_card_result(result)
        return [], summary
    cards = result["cards"]
    labels = labels or [f"Draw {i + 1}" for i in range(len(cards))]
    lines = [f"- **{label}:** {card}" for label, card in zip(labels, cards)]
    block = "\n".join(lines)
    summary = format_card_result(result)
    return cards, f"{summary}\n\n{block}"


def _table_lookup_prompt(
    table_name: str,
    page: str,
    pulled: list[str],
    labels: list[str],
    extra: str = "",
) -> str:
    entries = "\n".join(f"- {label}: {card}" for label, card in zip(labels, pulled))
    return (
        f"Brambletrek Core Rulebook — {table_name} ({page}).\n"
        f"Pulled from the table deck:\n{entries}\n\n"
        f"For each pull, state the card-value band (Ace, 2-4, 5-7, 8-10, Jack, Queen, King) "
        f"and quote or summarize the matching table row. {extra}"
    ).strip()


def run_shortcut(
    shortcut_id: str,
    game_id: str = GAME_BRAMBLETREK,
    *,
    in_aldwund: bool = False,
    reason_band: str = "",
    active_adventure: str = "",
    legacy: str = "",
    char_id: str | None = None,
    card_source: str = "virtual",
    combat_context: dict | None = None,
) -> ShortcutRun:
    """Build user-visible text and the prompt for the answer pipeline."""
    draw_kw = {"char_id": char_id, "card_source": card_source}
    if shortcut_id in _CARD_RAG_PROMPTS:
        prompt = _CARD_RAG_PROMPTS[shortcut_id]
        return {
            "user_message": prompt,
            "prompt": prompt,
            "kind": "card_rag",
        }

    if shortcut_id in ("recovery_health", "recovery_morale", "recovery_supplies"):
        stat = shortcut_id.replace("recovery_", "")
        cards, deck_block = _draw_lines(game_id, 1, [f"{stat.title()} recovery"], **draw_kw)
        if not cards:
            return {"user_message": deck_block, "prompt": deck_block, "kind": "multi_draw_rag"}
        curated = format_recovery_draw(stat, cards[0])
        prompt = (
            f"Brambletrek {stat.title()} Recovery (Core Rulebook p. 16).\n"
            f"Card pulled: {cards[0]}\n{curated}\n\n"
            "Expand this recovery prompt into a short narrative for my Gnawborn. "
            "Remind me how much Health/Morale/Supplies to restore when leaving recovery."
        )
        user = f"**{stat.title()} recovery**\n\n{deck_block}\n\n{curated}"
        return {"user_message": user, "prompt": prompt, "kind": "multi_draw_rag"}

    if shortcut_id == "legacy_overview":
        prompt = (
            "Summarize the six Brambletrek Legacies (Seer, Scrapper, Storyteller, Seeker, "
            "Sneaker, Soother) from the Core Rulebook: what each is good at, and how stat "
            "boosts and flaws apply after you assign resource cards."
        )
        return {"user_message": prompt, "prompt": prompt, "kind": "rag_only"}

    if shortcut_id == "reason_ending":
        reason_label = label_for_band("reasons", reason_band) if reason_band else ""
        curated = format_reason_ending(reason_band, reason_label=reason_label)
        prompt = (
            f"{curated}\n\n"
            "Narrate this Reason ending for my Gnawborn. Offer both options from the rules: "
            "a true ending, or staying in Hyhill to continue later. "
            "Use the Core Rulebook p. 36 and any indexed context; do not invent a different Reason."
        )
        user = f"**Reason ending** — how does my story conclude?\n\n{curated}"
        return {"user_message": user, "prompt": prompt, "kind": "rag_only"}

    if shortcut_id == "adventure_scene":
        if not active_adventure:
            msg = _adventure_select_help(for_scene=True)
            return {"user_message": msg, "prompt": msg, "kind": "static"}
        adv = adventure_meta(active_adventure)
        label = adv.get("label", active_adventure)
        n, paired, exploration_table = _adventure_draw_plan(active_adventure)
        draw_count = n * 2 if paired else n
        labels = []
        if paired:
            for i in range(n):
                labels.extend([f"Activity {i + 1} route", f"Activity {i + 1} result"])
        else:
            labels = [f"Event {i + 1}" for i in range(n)]
        cards, deck_block = _draw_lines(game_id, draw_count, labels, **draw_kw)
        if not cards:
            return {"user_message": deck_block, "prompt": deck_block, "kind": "multi_draw_rag"}
        route_cards = cards[:n]
        activity_cards = cards[n : n * 2] if paired else None
        curated = format_adventure_scene(
            active_adventure,
            route_cards,
            activity_cards,
            scene_table=exploration_table,
        )
        ctx = format_adventure_context(active_adventure)
        source = str(adv.get("source_label", "") or "").strip()
        page_hint = ""
        pmin, pmax = adv.get("pdf_page_min"), adv.get("pdf_page_max")
        if pmin is not None and pmax is not None:
            page_hint = f" PDF pages {pmin}–{pmax}."
        if curated:
            prompt = (
                f"{ctx}\n\n"
                f"Brambletrek adventure scene — **{label}** ({source}).{page_hint}\n"
                f"{curated}\n\n"
                "Using the curated rows above as ground truth, narrate each pull in order. "
                "Do not contradict listed stat changes, Combat, (LORE), or (ITEM) tags."
            )
            user = (
                f"**Adventure scene** — {label} ({n} pulls, resolve in order).\n\n"
                f"{deck_block}\n\n{curated}"
            )
            journey_cards = route_cards if not paired else cards
            return {
                "user_message": user,
                "prompt": prompt,
                "kind": "multi_draw_rag",
                "journey_cards": journey_cards,
            }
        ctx = format_adventure_context(active_adventure)
        page_hint = ""
        pmin, pmax = adv.get("pdf_page_min"), adv.get("pdf_page_max")
        if pmin is not None and pmax is not None:
            page_hint = f" Prefer {source} PDF pages {pmin}–{pmax}."
        prompt = (
            f"{ctx}\n\n"
            f"Brambletrek adventure scene — **{label}** ({source}).{page_hint}\n"
            f"Pulled from the table deck:\n"
            + "\n".join(f"- Scene {i + 1}: {c}" for i, c in enumerate(route_cards))
            + "\n\n"
            "Interpret each pull using the adventure module text in the indexed PDF only. "
            "Do not use curated Hyhill Journey & Exploration tables (pages 24–25) unless "
            "the adventure text explicitly says to. Quote or paraphrase the matching scene, "
            "option, or table row for each card. Resolve in order. Note when core combat, "
            "recovery, or journey rules apply."
        )
        user = (
            f"**Adventure scene** — {label} ({n} cards, resolve in order).\n\n"
            f"{deck_block}\n\n"
            "_Scenes come from the adventure PDF via rules lookup — not curated journey rows._"
        )
        return {"user_message": user, "prompt": prompt, "kind": "multi_draw_rag"}

    if shortcut_id == "adventure_overview":
        if not active_adventure:
            msg = _adventure_select_help(for_scene=False)
            return {"user_message": msg, "prompt": msg, "kind": "static"}
        ctx = format_adventure_context(active_adventure)
        adv = adventure_meta(active_adventure)
        label = adv.get("label", active_adventure)
        prompt = (
            f"{ctx}\n\n"
            f"Summarize how to run **{label}** using the indexed adventure PDF: "
            "opening hook, acts or scenes, how it uses Core journey/combat rules, "
            "and tips for the facilitator. Cite page numbers when available."
        )
        user = f"**Adventure overview** — {label}\n\n{ctx}"
        return {"user_message": user, "prompt": prompt, "kind": "rag_only"}

    if shortcut_id == "start_playing":
        prompt = (
            "Explain how to start playing Brambletrek from the Core Rulebook for someone "
            "who already has a Gnawborn character (Reason, Background, Trinket, resources, "
            "and Legacy assigned). Cover: each in-game day you draw four cards for Journey "
            "& Exploration (pages 24-25), resolve them in order, then rest. Mention combat "
            "when a face card says Combat, recovery tables on page 16, and that they can "
            "use the **Journey day (4 cards)** shortcut in Play → Shortcuts, or ask for "
            "'today's journey cards'."
        )
        user = "How do I start playing Brambletrek with my character ready?"
        return {"user_message": user, "prompt": prompt, "kind": "rag_only"}

    if shortcut_id == "random_legacy":
        roll = roll_dice("d6")
        legacy_label = legacy_by_roll(roll["total"])
        leg_id = legacy_id_by_roll(roll["total"])
        user = f"Random Legacy — {format_dice_result(roll)}\n\nRolled: **{legacy_label}**"
        prompt = (
            f"I rolled d6 for a random Legacy and got {roll['total']} ({legacy_label}, id={leg_id}). "
            f"Explain this Legacy from the Core Rulebook (abilities, stat boost, and flaw) "
            f"and how it fits character creation."
        )
        return {"user_message": user, "prompt": prompt, "kind": "roll_rag"}

    if shortcut_id == "resources":
        cards, deck_block = _draw_lines(
            game_id,
            6,
            ["Resource 1", "Resource 2", "Resource 3", "Resource 4", "Resource 5", "Resource 6"],
            **draw_kw,
        )
        if not cards:
            return {"user_message": deck_block, "prompt": deck_block, "kind": "multi_draw_rag"}
        prompt = _table_lookup_prompt(
            "Character Resources",
            "pages 15-16",
            cards,
            [f"Resource {i + 1}" for i in range(6)],
            extra=(
                "Explain how to assign these six pulls to Health, Morale, and Supplies "
                "(two cards per stat, Ace=11, J/Q/K=10, max 20 per stat). Mention the rule "
                "that if a pair totals 6 or less you may draw one extra card for that stat."
            ),
        )
        user = (
            f"**Character resources** — six cards for Health, Morale, and Supplies.\n\n{deck_block}"
        )
        return {"user_message": user, "prompt": prompt, "kind": "multi_draw_rag"}

    if shortcut_id in ("journey_day", "aldwund_day"):
        use_depths = in_aldwund or shortcut_id == "aldwund_day"
        title = "Aldwund day" if use_depths else "Journey day"
        adv_label = ""
        if not use_depths and active_adventure and module_has_curated_tables(active_adventure):
            adv = adventure_meta(active_adventure)
            adv_label = f" — {adv.get('label', active_adventure)}"
            title = (
                f"Adventure day{adv_label}"
                if module_scene_tables(active_adventure).get("choose_adventure")
                else f"Journey day{adv_label}"
            )
        n, paired, exploration_table = (
            (4, False, "") if use_depths else _adventure_draw_plan(active_adventure)
        )
        if use_depths:
            n = 4
        draw_count = n * 2 if paired else n
        label_stem = "Activity" if paired else "Event"
        labels = []
        if paired:
            for i in range(n):
                labels.extend([f"{label_stem} {i + 1} route", f"{label_stem} {i + 1} result"])
        else:
            labels = [f"{label_stem} {i + 1}" for i in range(n)]
        cards, deck_block = _draw_lines(game_id, draw_count, labels, **draw_kw)
        if not cards:
            return {"user_message": deck_block, "prompt": deck_block, "kind": "multi_draw_rag"}
        route_cards = cards[:n]
        activity_cards = cards[n : n * 2] if paired else None
        adventure_id = "" if use_depths else active_adventure
        curated = ""
        if adventure_id:
            curated = format_adventure_scene(
                adventure_id,
                route_cards,
                activity_cards,
                scene_table=exploration_table,
            )
        if not curated:
            event_labels = [f"Event {i + 1}" for i in range(len(route_cards))]
            curated = format_journey_events(
                route_cards,
                event_labels,
                in_aldwund=use_depths,
                adventure_id=adventure_id,
            )
        pages = "26–27 (Aldwund depths)" if use_depths else "24–25 (surface)"
        if adventure_id and module_journey_tables(adventure_id):
            pages = f"module tables ({n} cards/day)"
        prompt = (
            f"Brambletrek {title} — {n} card(s) (resolve in order)"
            + (" + activity results" if paired else "")
            + f", tables pp. {pages}.\n"
            f"{curated}\n\n"
            "Using the curated rows above as ground truth, write a brief narrative "
            "for each event in order. Do not contradict the listed stat changes, "
            "Combat, (DEPTHS), (EXIT), (LORE), or (ITEM) tags."
        )
        user = (
            f"**{title}** — {n} exploration event(s) (resolve in order).\n\n"
            f"{deck_block}\n\n{curated}"
        )
        return {
            "user_message": user,
            "prompt": prompt,
            "kind": "multi_draw_rag",
            "journey_cards": route_cards if not paired else cards,
        }

    if shortcut_id == "combat_setup":
        cards, deck_block = _draw_lines(
            game_id,
            6,
            [
                "Your initiative",
                "Opponent initiative",
                "Your tactic 1",
                "Your tactic 2",
                "Your tactic 3",
                "Your tactic 4",
            ],
            **draw_kw,
        )
        if not cards:
            return {"user_message": deck_block, "prompt": deck_block, "kind": "multi_draw_rag"}
        legacy_label = get_legacy_options().get(legacy, {}).get("label", legacy)
        curated = format_combat_setup_curated(
            cards,
            legacy_id=legacy,
            legacy_label=legacy_label,
            adventure_id=active_adventure,
            combat_context=combat_context,
        )
        ref = combat_reference_summary() if not curated else ""
        prompt = _table_lookup_prompt(
            "Combat setup",
            "pages 30-31",
            cards,
            [
                "Your initiative",
                "Opponent initiative",
                "Your tactic 1",
                "Your tactic 2",
                "Your tactic 3",
                "Your tactic 4",
            ],
            extra=(
                "Use the curated combat reference below (initiative, opponent tactics, "
                "and your Legacy tactic effects). Do not say tables are missing. "
                "Who goes first (Ace=11, face=10)? Summarize opponent type by suit. "
                "Explain each tactic in your hand for round 1 in plain language."
            ),
        )
        curated_block = f"\n\n{curated}" if curated else ""
        ref_block = f"\n\n{ref}" if ref and not curated else ""
        prompt = f"{prompt}{curated_block}{ref_block}"
        user = (
            "**Combat setup** — initiative (2) plus four tactic cards for your hand.\n\n"
            f"{deck_block}{curated_block}"
        )
        return {"user_message": user, "prompt": prompt, "kind": "multi_draw_rag"}

    if shortcut_id == "overcome_odds":
        cards, deck_block = _draw_lines(game_id, 2, ["Ability", "Outcome"], **draw_kw)
        if not cards:
            return {"user_message": deck_block, "prompt": deck_block, "kind": "multi_draw_rag"}
        prompt = _table_lookup_prompt(
            "Overcome the Odds skill check",
            "Basic Rules / Legacies section",
            cards,
            ["Ability", "Outcome"],
            extra=(
                "Compare Ability vs Outcome (Ace critical success, 2 critical failure). "
                "State pass or fail and any combat surprises from the rules."
            ),
        )
        user = f"**Overcome the odds** — Ability vs Outcome.\n\n{deck_block}"
        return {"user_message": user, "prompt": prompt, "kind": "multi_draw_rag"}

    if shortcut_id == "random_character":
        if card_source == "physical":
            msg = (
                "**Physical deck mode** — draw Reason, Background, Trinket, and six Resource "
                "cards from your real deck, report each, then ask for random Gnawborn "
                "table meanings."
            )
            return {"user_message": msg, "prompt": msg, "kind": "multi_draw_rag"}
        reason = draw_cards(count=1, game_id=game_id, char_id=char_id)
        if not reason.get("ok"):
            msg = format_card_result(reason)
            return {"user_message": msg, "prompt": msg, "kind": "multi_draw_rag"}
        bg = draw_cards(count=1, game_id=game_id, char_id=char_id)
        trinket = draw_cards(count=1, game_id=game_id, char_id=char_id)
        resources = draw_cards(count=6, game_id=game_id, char_id=char_id)
        if not bg.get("ok") or not trinket.get("ok") or not resources.get("ok"):
            msg = "Could not complete random character — deck may be low. Reset the deck and try again."
            return {"user_message": msg, "prompt": msg, "kind": "multi_draw_rag"}

        r, b, t = reason["cards"][0], bg["cards"][0], trinket["cards"][0]
        res = resources["cards"]
        deck_block = (
            f"{format_card_result(reason)}\n"
            f"{format_card_result(bg)}\n"
            f"{format_card_result(trinket)}\n"
            f"{format_card_result(resources)}\n\n"
            f"- **Reason for adventure:** {r}\n"
            f"- **Background:** {b}\n"
            f"- **Trinket:** {t}\n"
            + "".join(f"- **Resource {i + 1}:** {c}\n" for i, c in enumerate(res))
        )
        prompt = (
            "Brambletrek random Gnawborn character creation (Core Rulebook pages 10-16).\n"
            f"Pulled from the table deck:\n"
            f"- Reason for adventure: {r}\n"
            f"- Background: {b}\n"
            f"- Trinket: {t}\n"
            + "".join(f"- Resource {i + 1}: {c}\n" for i, c in enumerate(res))
            + "\n"
            "For each pull, give the card-value band and matching table row (Reason, Background, "
            "Trinket). For the six resource cards, suggest how to split them across Health, "
            "Morale, and Supplies (Ace=11, J/Q/K=10, max 20). Remind me to pick a Legacy "
            "(Seer, Scrapper, Storyteller, Seeker, Sneaker, or Soother) and apply its stat "
            "boost and flaw after assigning resources."
        )
        user = f"**Random character** — Reason, Background, Trinket, and six resource pulls.\n\n{deck_block}"
        return {"user_message": user, "prompt": prompt, "kind": "multi_draw_rag"}

    raise ValueError(f"Unknown Brambletrek shortcut: {shortcut_id}")


SHORTCUTS: list[dict[str, str]] = [
    {"id": s["id"], "label": s["label"], "kind": s["kind"]} for s in BRAMBLETREK_SHORTCUTS
]


def shortcuts_list_for_character(active_adventure: str = "") -> list[dict[str, str]]:
    return [
        {"id": s["id"], "label": s["label"], "kind": s["kind"]}
        for s in shortcuts_for_character(active_adventure=active_adventure)
    ]


def run_shortcut_for_plugin(shortcut_id: str, **char) -> dict:
    """Adapter for GamePlugin.run_shortcut (auto-dm DM graph)."""
    game_id = str(char.get("game_id") or GAME_BRAMBLETREK)
    run = run_shortcut(
        shortcut_id,
        game_id=game_id,
        in_aldwund=bool(char.get("in_aldwund")),
        reason_band=str(char.get("reason_band") or ""),
        active_adventure=str(char.get("active_adventure") or ""),
        legacy=str(char.get("legacy") or ""),
        char_id=str(char.get("id") or "") or None,
        card_source=str(char.get("card_source") or "virtual"),
        combat_context=char.get("combat_context")
        if isinstance(char.get("combat_context"), dict)
        else None,
    )
    kind = run.get("kind", "static")
    base = {
        "user_message": run.get("user_message", ""),
        "prompt": run.get("prompt", ""),
        "summary": run.get("user_message", ""),
    }
    if kind == "static":
        return {**base, "task": "rules_help"}
    if kind in {"rag_only", "multi_draw_rag", "roll_rag", "card_rag"}:
        out = {**base, "task": "rag_direct"}
        if run.get("journey_cards"):
            out["journey_cards"] = run["journey_cards"]
            out["journey_shortcut_id"] = shortcut_id
        return out
    return {**base, "task": "rag_direct"}
