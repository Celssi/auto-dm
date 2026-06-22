"""AI scene prose for D&D 5e (ai_narrator story mode)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.dm.prose_style import NARRATION_STYLE_RULES, sanitize_narration_dashes
from backend.games.dnd5e.characters.entity import Dnd5eCharacter, campaign_setting_line
from backend.llm import ChatProvider, get_langchain_chat_llm, invoke_chat_llm


def synthesize_journal_entry(
    mechanics: str,
    *,
    entity: Dnd5eCharacter,
    story_so_far: str = "",
    chat_provider: ChatProvider = "ollama",
) -> str:
    llm = get_langchain_chat_llm(chat_provider)
    who = entity.name.strip() or "the adventurer"
    role = f"{entity.species} {entity.class_name}".strip() or "hero"
    prior = ""
    if story_so_far.strip():
        prior = f"\n\n{story_so_far.strip()[:3500]}\n"
    setting = campaign_setting_line(entity)
    prompt = f"""You are the Dungeon Master for a D&D 5e solo session.
{setting}
Write 2-4 short paragraphs in third person past tense for {who} ({role}, level {entity.level}).
Use the mechanical results below; do not explain dice or rules. Plain prose only.

{NARRATION_STYLE_RULES}

{prior}
Mechanics:
{mechanics[:3000]}
"""
    response = invoke_chat_llm(
        llm,
        [
            SystemMessage(
                content=(
                    "Write evocative fantasy GM narration for a tabletop RPG. "
                    "Never use em dashes or en dashes in prose."
                )
            ),
            HumanMessage(content=prompt),
        ],
        agent="journal_narrator",
        provider=chat_provider,
    )
    text = response.content if isinstance(response.content, str) else str(response.content)
    return sanitize_narration_dashes(text.strip())


def synthesize_lonelog_summary(
    prose: str,
    *,
    chat_provider: ChatProvider = "ollama",
) -> str:
    llm = get_langchain_chat_llm(chat_provider)
    prompt = f"""Summarize this D&D scene in 1–2 short sentences for a session log.
Past tense, in-world. No rulebook language.

{prose[:4000]}
"""
    response = invoke_chat_llm(
        llm,
        [
            SystemMessage(content="Write a very concise in-world summary."),
            HumanMessage(content=prompt),
        ],
        agent="scribe",
        provider=chat_provider,
    )
    text = response.content if isinstance(response.content, str) else str(response.content)
    return text.strip()
