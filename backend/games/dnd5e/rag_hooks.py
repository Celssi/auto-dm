"""D&D 5e RAG hooks."""

from __future__ import annotations

from backend.games.rag_hooks import GameRagHooks


def _dnd_system_prompt(factions: list[str] | None) -> str:
    scope = ", ".join(factions) if factions else "Player's Handbook, DMG, Monster Manual"
    return f"""You are a D&D 5e (2024) rules assistant for solo play.
Answer using ONLY the provided rule excerpts from: {scope}.
Cite sources as [Book p.X]. If unsure, say so.
Keep answers concise and actionable for a solo player."""


DND_RAG_HOOKS = GameRagHooks(
    system_prompt=_dnd_system_prompt,
    ingest_hint="python -m backend.rag.ingest --core",
)
