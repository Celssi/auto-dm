"""Resolve Monster Manual stat blocks via RAG."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.llm import get_langchain_chat_llm
from backend.rag.engine import query_rules


class MonsterAttack(BaseModel):
    name: str = "Attack"
    to_hit: int = 0
    damage: str = "1d6"


class MonsterStats(BaseModel):
    name: str
    ac: int = 12
    hp: int = 10
    speed: str = "30 ft."
    attacks: list[MonsterAttack] = Field(default_factory=list)
    multiattack_count: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Number of attacks per Multiattack action (1 = no multiattack)",
    )


def _fallback_stats(monster_name: str) -> MonsterStats:
    return MonsterStats(
        name=monster_name,
        ac=12,
        hp=22,
        attacks=[MonsterAttack(name="Claw", to_hit=4, damage="1d6+2")],
    )


@lru_cache(maxsize=128)
def lookup_monster(monster_name: str) -> MonsterStats:
    """Fetch and parse a monster stat block from the Monster Manual index."""
    name = (monster_name or "").strip()
    if not name:
        return _fallback_stats("Unknown")

    rag = query_rules(
        f"{name} stat block AC HP attacks",
        factions=["monsters"],
        top_k=6,
        use_rerank=True,
        generate_answer=False,
    )
    if not rag.sources:
        return _fallback_stats(name)

    chunks = []
    for i, src in enumerate(rag.sources[:5], 1):
        chunks.append(
            f"[{i}] {src.get('source_label', '?')} p.{src.get('page', '?')}\n"
            f"{src.get('text', '')[:1200]}"
        )
    context = "\n\n".join(chunks)

    llm = get_langchain_chat_llm("claude").with_structured_output(MonsterStats)
    prompt = f"""Extract the D&D 5e stat block for "{name}" from these Monster Manual excerpts ONLY.

Rules:
- Use ONLY numbers present in the excerpts. Do not invent stats.
- ac: Armor Class integer
- hp: Hit Points (use average if a range is given)
- attacks: primary melee/ranged attacks with to_hit bonus and damage dice
- multiattack_count: how many attacks the creature makes per Multiattack action
  (e.g. "makes two Claw attacks" → 2, "makes three attacks" → 3).
  Set to 1 if the creature has no Multiattack.
- If excerpts do not contain this creature, set ac=12, hp=22, one generic attack +4, 1d6+2

Excerpts:
{context[:6000]}
"""
    try:
        stats = llm.invoke([HumanMessage(content=prompt)])
        if not stats.name.strip():
            stats.name = name
        if not stats.attacks:
            stats.attacks = [MonsterAttack(name="Attack", to_hit=4, damage="1d6+2")]
        return stats
    except Exception:
        return _fallback_stats(name)
