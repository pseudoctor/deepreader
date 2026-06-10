"""Chapter detection and text utility helpers."""

from __future__ import annotations

import re

WORDS_PER_TOKEN = 0.75


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "reading-workspace"


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) / WORDS_PER_TOKEN)


CHAPTER_PATTERNS = [
    re.compile(
        r"^\s*(?:#{1,6}\s*)?(chapter|ch\.?|cap[ií]tulo)\s+(\d{1,3})\b[:.\-\s]*(.*)$", re.IGNORECASE
    ),
    re.compile(r"^\s*(?:#{1,6}\s*)?(\d{1,2})[.)]\s+([A-Z][^\n]{3,100})$"),
]


def detect_chapters(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    chapters: list[dict[str, object]] = []
    seen: set[str] = set()
    for idx, line in enumerate(lines, start=1):
        clean = line.strip()
        if len(clean) > 140:
            continue
        for pattern in CHAPTER_PATTERNS:
            match = pattern.match(clean)
            if not match:
                continue
            if pattern is CHAPTER_PATTERNS[0]:
                number = match.group(2).zfill(2)
                title = match.group(3).strip(" .:-") or f"Chapter {int(match.group(2))}"
            else:
                number = match.group(1).zfill(2)
                title = match.group(2).strip()
            key = f"ch{number}"
            if key not in seen:
                seen.add(key)
                chapters.append({"id": key, "title": title, "line": idx})
            break
    if not chapters:
        chapters.append({"id": "ch01", "title": "Full Text", "line": 1})
    return chapters[:120]
