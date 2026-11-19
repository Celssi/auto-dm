"""Page chunking used by ingest. Kept free of Chroma so tests can import it."""

from __future__ import annotations

import re

from backend.rag.text_utils import is_meaningful

MIN_CHUNK_CHARS = 300
_TABLE_DICE_RE = re.compile(r"\b\d+d\d+\b")

# ALL CAPS / chapter titles only. Title Case one-liners like "Greataxe" used to
# split the weapons table so the name and mastery lived in different chunks.
SECTION_HEADING_RE = re.compile(
    r"^(?:"
    r"CHAPTER\s+\d+\b.*|"
    r"APPENDIX\s+[A-Z0-9].*|"
    r"[A-Z][A-Z0-9][A-Z0-9 ,/'&-]{2,70}"
    r")$"
)


def keep_chunk(text: str) -> bool:
    if is_meaningful(text, min_chars=25, min_alpha_ratio=0.12):
        return True
    compact = re.sub(r"\s+", "", text)
    has_letters = bool(re.search(r"[A-Za-z]{3,}", text))
    has_numbers = bool(re.search(r"\d", text))
    return len(compact) >= 20 and has_letters and has_numbers


def _hard_split(text: str, chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _split_long_paragraph(paragraph: str, chunk_size: int) -> list[str]:
    if len(paragraph) <= chunk_size:
        return [paragraph]
    sentence_parts = re.split(r"(?<=[.!?])\s+", paragraph)
    if len(sentence_parts) <= 1:
        return _hard_split(paragraph, chunk_size)
    out: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for sent in sentence_parts:
        sent = sent.strip()
        if not sent:
            continue
        if len(sent) > chunk_size:
            if buf:
                out.append(" ".join(buf))
                buf = []
                buf_len = 0
            out.extend(_hard_split(sent, chunk_size))
            continue
        add_len = len(sent) + (1 if buf else 0)
        if buf and buf_len + add_len > chunk_size:
            out.append(" ".join(buf))
            buf = [sent]
            buf_len = len(sent)
        else:
            buf.append(sent)
            buf_len += add_len
    if buf:
        joined = " ".join(buf)
        if len(joined) > chunk_size:
            out.extend(_hard_split(joined, chunk_size))
        else:
            out.append(joined)
    return out


def detect_section_title(text: str) -> str:
    for line in text.split("\n")[:3]:
        line = line.strip()
        if not line or len(line) > 80:
            continue
        if SECTION_HEADING_RE.match(line):
            return line
    return ""


def split_into_sections(text: str) -> list[tuple[str, str]]:
    lines = text.split("\n")
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if (
            stripped
            and len(stripped) <= 80
            and SECTION_HEADING_RE.match(stripped)
            and current_lines
            and len("\n".join(current_lines).strip()) > 20
        ):
            sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = stripped
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_title, body))

    return sections if len(sections) > 1 else [("", text)]


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if keep_chunk(text) else []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    expanded: list[str] = []
    for para in paragraphs:
        expanded.extend(_split_long_paragraph(para, chunk_size))

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for part in expanded:
        add_len = len(part) + (2 if current else 0)
        if current and current_len + add_len > chunk_size:
            chunks.append("\n\n".join(current).strip())
            if overlap > 0:
                tail = chunks[-1][-overlap:].strip()
                current = [tail, part] if tail else [part]
                current_len = len("\n\n".join(current))
            else:
                current = [part]
                current_len = len(part)
            continue
        current.append(part)
        current_len += add_len
    if current:
        chunks.append("\n\n".join(current).strip())

    capped: list[str] = []
    for chunk in chunks:
        capped.extend(_hard_split(chunk, chunk_size))
    return [c for c in capped if keep_chunk(c)]


def looks_like_table(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 6:
        return False
    short = sum(1 for ln in lines if len(ln) <= 48)
    dice = len(_TABLE_DICE_RE.findall(text))
    return (short / len(lines) >= 0.5 and dice >= 3) or dice >= 8


def merge_short_chunks(
    chunks: list[tuple[str, str]], min_chars: int = MIN_CHUNK_CHARS
) -> list[tuple[str, str]]:
    if not chunks:
        return []
    merged: list[tuple[str, str]] = []
    for title, text in chunks:
        if merged and len(merged[-1][1]) < min_chars:
            prev_title, prev_text = merged[-1]
            merged[-1] = (prev_title or title, f"{prev_text}\n\n{text}".strip())
        else:
            merged.append((title, text))
    if len(merged) >= 2 and len(merged[-1][1]) < min_chars:
        t0, b0 = merged[-2]
        t1, b1 = merged[-1]
        merged[-2] = (t0 or t1, f"{b0}\n\n{b1}".strip())
        merged.pop()
    return merged


def chunk_page_with_sections(
    page_text: str, chunk_size: int, overlap: int
) -> list[tuple[str, str]]:
    if looks_like_table(page_text):
        header = next((ln.strip() for ln in page_text.splitlines() if ln.strip()), "")
        results: list[tuple[str, str]] = []
        for chunk in chunk_text(page_text, chunk_size, overlap):
            title = header if len(header) <= 80 else detect_section_title(chunk)
            results.append((title, chunk))
        return merge_short_chunks(results)
    sections = split_into_sections(page_text)
    results: list[tuple[str, str]] = []
    for title, body in sections:
        for chunk in chunk_text(body, chunk_size, overlap):
            chunk_title = title or detect_section_title(chunk)
            results.append((chunk_title, chunk))
    return merge_short_chunks(results)
