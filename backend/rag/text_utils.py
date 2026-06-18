"""Shared text cleaning for ingest and OCR."""

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    # Join words split across line breaks in PDF/OCR output.
    text = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", text)
    # Collapse noisy whitespace while preserving paragraph boundaries.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return text.strip()


def is_meaningful(
    text: str,
    min_chars: int = 40,
    min_alpha_ratio: float = 0.25,
) -> bool:
    stripped = re.sub(r"[\s™\n]+", "", text)
    if len(stripped) < min_chars:
        return False
    alpha = sum(1 for c in stripped if c.isalpha())
    ratio = alpha / max(1, len(stripped))
    return ratio >= min_alpha_ratio


def looks_garbled(text: str) -> bool:
    """Detect a broken PDF text layer (many one-letter tokens, tiny words, or
    fragmented lines), as seen in some official rulebook PDFs. Conservative:
    needs enough tokens before judging, so clean pages are never flagged."""
    tokens = re.findall(r"[A-Za-z]+", text)
    if len(tokens) < 25:
        return False
    avg_len = sum(len(t) for t in tokens) / len(tokens)
    single_ratio = sum(1 for t in tokens if len(t) == 1) / len(tokens)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    short_line_ratio = sum(1 for ln in lines if len(ln) <= 2) / len(lines) if lines else 0.0
    if avg_len < 2.8:
        return True
    if single_ratio > 0.30 and avg_len < 3.6:
        return True
    if short_line_ratio > 0.55:
        return True
    return False


def is_low_quality(
    text: str,
    min_chars: int = 60,
    min_alpha_ratio: float = 0.2,
) -> bool:
    """A page worth re-OCRing: too sparse OR a garbled text layer."""
    return not is_meaningful(text, min_chars, min_alpha_ratio) or looks_garbled(text)
