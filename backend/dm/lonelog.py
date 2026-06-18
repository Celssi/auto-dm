"""Lonelog formatting for D&D sessions."""

from __future__ import annotations

import re
from datetime import datetime, timezone

LOG_TIMESTAMP = re.compile(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*$")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def format_mechanical(text: str) -> str:
    return f"@ {_now()} {text.strip()}"


def format_narrative(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return "\n".join(f"=> {ln}" for ln in lines)


def read_tail(content: str, n_lines: int = 50) -> list[str]:
    lines = content.splitlines()
    return lines[-n_lines:] if len(lines) > n_lines else lines


def _is_skipped_line(ln: str) -> bool:
    if not ln:
        return True
    if ln.startswith("#"):
        return True
    if ln in ("_Lonelog session log_",):
        return True
    if ln.startswith("_") and ln.endswith("_"):
        return True
    return False


def extract_narrative_snippets(content: str) -> list[str]:
    """Pull narrative beats from auto-dm lonelog (=>) or ChatDM adventure log (### timestamps)."""
    snippets: list[str] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("=>"):
            text = ln[2:].strip()
            if text:
                snippets.append(text)
            i += 1
            continue
        if LOG_TIMESTAMP.match(ln):
            i += 1
            body_lines: list[str] = []
            while i < len(lines):
                nxt = lines[i].strip()
                if LOG_TIMESTAMP.match(nxt) or nxt.startswith("## "):
                    break
                if not _is_skipped_line(nxt):
                    body_lines.append(nxt)
                i += 1
            if body_lines:
                snippets.append(" ".join(body_lines))
            continue
        i += 1
    return snippets


def build_lonelog_markdown(snippets: list[str], *, note: str = "") -> str:
    parts = ["# Lonelog", ""]
    if note.strip():
        parts.append(f"_{note.strip()}_")
        parts.append("")
    for snippet in snippets:
        parts.append(f"=> {snippet}")
    return "\n".join(parts).rstrip() + "\n"


def adventure_log_to_lonelog(adventure_log: str, *, note: str = "") -> str:
    """Convert adventure log (ChatDM or mixed) into session lonelog markdown."""
    snippets = extract_narrative_snippets(adventure_log)
    return build_lonelog_markdown(snippets, note=note)


def narrative_context_for_ai(
    log_content: str,
    *,
    campaign_setting: str = "freeform",
    campaign_notes: str = "",
    max_entries: int = 8,
    max_chars: int = 3500,
) -> str:
    snippets = extract_narrative_snippets(log_content)
    if not snippets:
        return ""
    body = "\n\n".join(snippets[-max_entries:])
    if len(body) > max_chars:
        body = body[-max_chars:].lstrip()
    setting = (campaign_setting or "freeform").strip().lower()
    notes = (campaign_notes or "").strip()
    if setting == "faerun":
        prefix = "Story so far in Faerûn (continue naturally):"
    elif notes:
        prefix = f"Story so far in this campaign (continue naturally):\nSetting: {notes}"
    else:
        prefix = "Story so far (continue naturally):"
    return f"{prefix}\n\n{body}"
