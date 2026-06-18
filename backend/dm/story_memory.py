"""Narrative memory: adventure canon summary + recent scenes for DM context."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.characters.entity import Dnd5eCharacter
from backend.dm.lonelog import extract_narrative_snippets
from backend.dm.world_context import world_context_for_campaign
from backend.llm import get_langchain_chat_llm, invoke_chat_llm

CANON_MAX = 4000
RECENT_MAX = 3000
RECENT_ENTRIES = 10

SUMMARY_SECTIONS = """## Premise
## Major beats (chronological)
## Current situation
## Established facts (do not contradict)
## Open mysteries & hooks"""


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def recent_scenes_from_log(log_content: str, *, max_entries: int = RECENT_ENTRIES, max_chars: int = RECENT_MAX) -> str:
    snippets = extract_narrative_snippets(log_content)
    if not snippets:
        return ""
    body = "\n\n".join(snippets[-max_entries:])
    return _clip(body, max_chars)


def build_narrative_context(
    adventure: dict[str, Any],
    campaign_id: str | None,
    character: Dnd5eCharacter | None,
) -> dict[str, str]:
    """Assemble layered memory for narrator and continuity guard."""
    canon = _clip(adventure.get("summary") or "", CANON_MAX)
    recent = recent_scenes_from_log(adventure.get("log") or "")
    has_canon = bool(canon.strip())
    world_bible = world_context_for_campaign(campaign_id, has_adventure_summary=has_canon)

    if character and recent:
        setting = (character.campaign_setting or "freeform").strip().lower()
        notes = (character.campaign_notes or "").strip()
        if setting == "faerun":
            prefix = "Most recent scenes (continue naturally from here):"
        elif notes:
            prefix = f"Most recent scenes in this campaign (continue naturally):\nSetting: {notes}"
        else:
            prefix = "Most recent scenes (continue naturally from here):"
        recent = f"{prefix}\n\n{recent}"

    return {
        "canon_summary": canon,
        "recent_scenes": recent,
        "world_bible": world_bible,
    }


def build_offline_summary(
    *,
    log: str = "",
    outline: str = "",
    story_arc: str = "",
) -> str:
    """Deterministic canon summary without LLM (migration / backfill fallback)."""
    snippets = extract_narrative_snippets(log)
    beats = "\n".join(f"- {s}" for s in snippets) if snippets else "- (no log entries yet)"
    current = snippets[-1] if snippets else (outline[:500] or story_arc[:500] or "Adventure beginning.")
    premise = outline.strip()[:1200] or story_arc.strip()[:1200] or "Solo D&D adventure."
    arc_tail = story_arc.strip()[-1500:] if story_arc else ""
    mysteries = ""
    if "MYSTERIES" in story_arc.upper() or "mysteries" in story_arc.lower():
        idx = story_arc.lower().find("mysteries")
        if idx >= 0:
            mysteries = story_arc[idx : idx + 1200].strip()
    if not mysteries:
        mysteries = "- Continue unresolved threads from the log and campaign journal."

    return f"""## Premise
{premise}

## Major beats (chronological)
{beats}

## Current situation
{current}

## Established facts (do not contradict)
- Facts in Major beats above are canonical.
- NPC and location details are in the campaign journal.
{('- Campaign notes: ' + arc_tail[:800]) if arc_tail else ''}

## Open mysteries & hooks
{mysteries}
"""


def generate_full_summary(
    *,
    log: str = "",
    outline: str = "",
    story_arc: str = "",
    npc_hints: str = "",
    opening_scene: str = "",
) -> str:
    """One-shot canon summary from adventure log or bootstrap material."""
    llm = get_langchain_chat_llm("claude")
    prompt = f"""Create an adventure canon summary for a D&D 5e solo campaign DM.

Use exactly these markdown sections:
{SUMMARY_SECTIONS}

Rules:
- Major beats: chronological bullet list of key plot events
- Established facts: concrete truths the DM must not contradict (NPC status, locations, items, seals, deaths)
- Current situation: where play should resume NOW (time, place, mood, immediate tensions)
- Open mysteries: unresolved questions and hooks
- Be factual; no speculation. Include character level if known from the log.

Adventure outline:
{outline[:2000] or '(none)'}

Campaign story arc:
{story_arc[:3000] or '(none)'}

NPC hints:
{npc_hints[:1500] or '(none)'}

Opening scene:
{opening_scene[:1500] or '(none)'}

Adventure log:
{log[:12000] or '(empty — use outline and story arc only)'}
"""
    response = invoke_chat_llm(
        llm,
        [
            SystemMessage(content="Write structured campaign canon for a tabletop RPG DM."),
            HumanMessage(content=prompt),
        ],
        agent="chronicler_full",
        provider="claude",
    )
    text = response.content if isinstance(response.content, str) else str(response.content)
    return text.strip()


def increment_summary(
    existing: str,
    *,
    user_message: str,
    dm_response: str,
    log_entry: str = "",
) -> str:
    """Update adventure canon after one play turn."""
    if not dm_response.strip():
        return existing
    llm = get_langchain_chat_llm("claude")
    prompt = f"""Update this adventure canon summary after one D&D solo play turn.

Keep exactly these sections:
{SUMMARY_SECTIONS}

Rules:
- Update Current situation to reflect the end of this turn
- Append one bullet to Major beats for this turn's key event
- Add/remove Established facts and Open mysteries as needed
- Do NOT drop important earlier facts
- Keep the full document under ~2500 words

Existing canon:
{existing[:6000] or '(empty — create initial canon from this turn)'}

Player action:
{user_message[:1500]}

DM response (canonical narration):
{dm_response[:3500]}

Log entry for this turn:
{log_entry[:500] or '(none)'}
"""
    response = invoke_chat_llm(
        llm,
        [
            SystemMessage(content="Maintain accurate campaign canon for a solo D&D DM."),
            HumanMessage(content=prompt),
        ],
        agent="chronicler",
        provider="claude",
    )
    text = response.content if isinstance(response.content, str) else str(response.content)
    return text.strip()
