"""Check DM narration against established canon and revise if needed."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.llm import get_langchain_chat_llm


class ContinuityVerdict(BaseModel):
    has_issues: bool = Field(description="True if the draft contradicts canon")
    issues: list[str] = Field(
        default_factory=list, description="Brief descriptions of contradictions"
    )
    revised_response: str = Field(
        default="",
        description="Full corrected DM response if has_issues, else empty string",
    )


def check_continuity(
    *,
    draft_response: str,
    user_message: str,
    canon_summary: str,
    world_bible: str,
    recent_scenes: str,
) -> ContinuityVerdict:
    if not draft_response.strip():
        return ContinuityVerdict(has_issues=False)

    prompt = f"""You are a continuity editor for a D&D 5e solo campaign.

Review the DM draft response against established canon. Check:
- NPC names, status (alive/dead/free/captured), location, relationships
- Place names and what happened where
- Plot facts: seals, items, quests, timeline, character level/abilities
- Tone and facts must match Recent scenes unless the player explicitly retcons

If the draft is consistent, set has_issues=false and leave revised_response empty.
If there are contradictions, set has_issues=true, list issues briefly, and provide a FULL revised DM response that:
- Fixes all contradictions
- Keeps the same narrative quality and length
- Preserves the player's intended action outcome
- Does not add meta commentary

## Adventure canon
{canon_summary[:4000] or "(none)"}

## World bible
{world_bible[:4000] or "(none)"}

## Recent scenes
{recent_scenes[:3000] or "(none)"}

Player message:
{user_message[:1500]}

DM draft:
{draft_response[:4000]}
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(ContinuityVerdict)
    return llm.invoke([HumanMessage(content=prompt)])


def apply_continuity_guard(
    *,
    draft_response: str,
    user_message: str,
    canon_summary: str,
    world_bible: str,
    recent_scenes: str,
) -> tuple[str, list[str]]:
    """Return (final_response, issues)."""
    if not draft_response.strip():
        return draft_response, []
    verdict = check_continuity(
        draft_response=draft_response,
        user_message=user_message,
        canon_summary=canon_summary,
        world_bible=world_bible,
        recent_scenes=recent_scenes,
    )
    if verdict.has_issues and verdict.revised_response.strip():
        return verdict.revised_response.strip(), verdict.issues
    return draft_response, verdict.issues if verdict.has_issues else []
