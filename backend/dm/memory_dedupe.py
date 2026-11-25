"""Keep NPC/location journal memory readable.

Journal entries grow by appending "[Update]" paragraphs after play turns. The extractor
often restates facts that are already in the notes with slightly different wording, so
merges go through these helpers to drop sentences that add nothing new. ``condense_body``
does the same for display only; it never rewrites stored data.
"""

from __future__ import annotations

import re
from functools import lru_cache

UPDATE_MARKER = "[Update]"

_WORD = re.compile(r"[a-z0-9']+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'*(])")
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "for", "with",
    "is", "are", "was", "were", "be", "been", "has", "have", "had", "her", "his", "their",
    "she", "he", "they", "it", "its", "that", "this", "as", "by", "from", "now", "who",
    "which", "into", "about", "after", "also", "you", "your", "them", "him",
}  # fmt: skip

# Bold phrases or extractor names that are really player options, not proper nouns.
_ACTION_VERBS = {
    "ask", "attack", "accept", "approach", "cast", "check", "climb", "continue", "decline",
    "enter", "examine", "explore", "follow", "go", "head", "help", "hide", "inspect",
    "investigate", "leave", "listen", "look", "offer", "open", "persuade", "question",
    "refuse", "rest", "return", "run", "search", "speak", "steal", "take", "talk", "tell",
    "travel", "try", "use", "visit", "wait", "warn", "grab", "dodge", "parry",
}  # fmt: skip
_RULE_NAME_BLOCKLIST = {
    "bless", "bane", "shield", "guidance", "hex", "hunter's mark", "hunters mark",
    "savage attacker", "great weapon fighting", "defense", "dueling",
    "disadvantage", "advantage", "opportunity attack", "action", "bonus action",
    "reaction", "hit dice", "lay on hands", "concentration", "initiative",
    "death save", "armor class", "spell slot", "cantrip", "unarmed strike",
    "grapple", "shove", "help", "hide", "search", "ready", "dash", "disengage",
}  # fmt: skip
# Words that mark a heading or rules/mechanics label rather than a person or place.
_RULE_TERM_WORDS = {
    "summary", "reminder", "reminders", "table", "tables", "recovery", "journey",
    "round", "tactic", "tactics", "rule", "rules", "note", "notes", "event", "events",
    "deck", "stat", "stats", "morale", "health", "supplies", "mechanics", "initiative",
    "outcome", "outcomes", "result", "results", "options", "next steps", "recap",
}  # fmt: skip
# UI / button labels and Brambletrek panel names, including single-word controls
# like "Apply" and "Combat" that otherwise look like proper nouns.
_UI_CONTROL_WORDS = {
    "apply", "applying", "applied", "start", "starting", "finish", "finishing",
    "discard", "discarding", "retreat", "retreating", "cancel", "close", "save",
    "saving", "reload", "refresh", "shuffle", "confirm", "submit", "previous",
    "panel", "shortcut", "shortcuts", "lonelog", "audit", "combat", "deck",
    "tactics", "resources", "heal", "defence", "defense", "healing",
}  # fmt: skip
_UI_CONTROL_PHRASES = {
    "finish day", "start combat", "apply to sheet", "apply previous first",
    "draw item", "new round", "today's draws", "record card",
}  # fmt: skip
_NAME_PARTICLES = {"of", "the", "de", "du", "van", "von", "da", "del", "la", "le", "and", "in"}


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "ly", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _content_words(text: str) -> set[str]:
    words = _WORD.findall(text.lower().replace("\u2019", "'"))
    return {_stem(w.removesuffix("'s")) for w in words if w not in _STOPWORDS and len(w) > 2}


def _similar(new: set[str], known: set[str]) -> float:
    """Share of the new sentence's content words that an existing sentence already has."""
    if not new or not known:
        return 0.0
    return len(new & known) / len(new)


def split_sentences(text: str) -> list[str]:
    parts: list[str] = []
    for para in re.split(r"\n\s*\n", text or ""):
        para = para.replace(UPDATE_MARKER, "").strip()
        if not para:
            continue
        parts.extend(s.strip() for s in _SENTENCE_SPLIT.split(para) if s.strip())
    return parts


def novel_sentences(addition: str, existing: str, *, threshold: float = 0.6) -> list[str]:
    """Sentences of ``addition`` that are not near-duplicates of anything in ``existing``."""
    known = [_content_words(s) for s in split_sentences(existing)]
    out: list[str] = []
    for sentence in split_sentences(addition):
        words = _content_words(sentence)
        if not words:
            continue
        if any(_similar(words, k) >= threshold for k in known):
            continue
        known.append(words)
        out.append(sentence)
    return out


def merge_update(existing: str, addition: str) -> str | None:
    """Return the new body with only genuinely new facts appended, or None if nothing new."""
    body = (existing or "").strip()
    fresh = novel_sentences(addition, body)
    if not fresh:
        return None
    text = " ".join(fresh)
    if not body:
        return text
    return f"{body}\n\n{UPDATE_MARKER}\n{text}"


def condense_body(body: str) -> str:
    """Display-only: drop [Update] paragraphs that repeat earlier notes."""
    text = (body or "").strip()
    if UPDATE_MARKER not in text:
        return text
    chunks = [c.strip() for c in text.split(UPDATE_MARKER)]
    kept = chunks[0]
    for chunk in chunks[1:]:
        if not chunk:
            continue
        merged = merge_update(kept, chunk)
        if merged is not None:
            kept = merged
    return kept


_CONDITION_NAMES = {
    "blinded",
    "charmed",
    "deafened",
    "frightened",
    "grappled",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "stunned",
    "unconscious",
}


@lru_cache(maxsize=1)
def _curated_item_names() -> frozenset[str]:
    """Item names from curated item tables (e.g. "Precious Minerals") are not NPCs."""
    try:
        import yaml

        from backend.config import CURATED_DIR
    except Exception:
        return frozenset()
    names: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            label = node.get("label")
            if isinstance(label, str) and 0 < len(label) <= 40:
                names.add(label.strip().lower())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for path in sorted(CURATED_DIR.glob("*items*.yaml")):
        try:
            walk(yaml.safe_load(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return frozenset(names)


def looks_like_entity_name(name: str) -> bool:
    """Reject player options such as "Ask Dalla to come with you" posing as names."""
    cleaned = re.sub(r"\s+", " ", (name or "").strip().strip("*").strip())
    if len(cleaned) < 2 or len(cleaned) > 60:
        return False
    if cleaned.lower() in _CONDITION_NAMES or cleaned.lower() in _RULE_NAME_BLOCKLIST:
        return False
    words = cleaned.split(" ")
    if len(words) > 6:
        return False
    lowered = cleaned.lower()
    if lowered in _UI_CONTROL_WORDS or lowered in _UI_CONTROL_PHRASES:
        return False
    if any(w.lower().strip("'\"(),:-") in _RULE_TERM_WORDS for w in words):
        return False
    if any(w.lower().strip("'\"(),:-") in _UI_CONTROL_WORDS for w in words):
        return False
    if lowered in _curated_item_names():
        return False
    if words[0].lower() in _ACTION_VERBS and len(words) > 1:
        return False
    if cleaned.endswith(("?", "!", ".")):
        return False
    for word in words[1:]:
        bare = word.strip("'\"(),-")
        if bare and bare[0].islower() and bare.lower() not in _NAME_PARTICLES:
            return False
    return True
