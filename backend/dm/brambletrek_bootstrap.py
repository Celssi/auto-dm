"""Backward-compatible re-exports — use games.brambletrek.dm.bootstrap instead."""

from backend.games.brambletrek.dm.bootstrap import (
    bootstrap_brambletrek_campaign,
    generate_brambletrek_opening,
)

__all__ = ["bootstrap_brambletrek_campaign", "generate_brambletrek_opening"]
