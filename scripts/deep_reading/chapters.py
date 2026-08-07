"""Chapter detection and text utility helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

WORDS_PER_TOKEN = 0.75
CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
ROMAN_DIGITS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "M": 1000}
TOC_MARKERS = {"目次", "目錄", "目录", "contents", "table of contents"}
TOC_PHRASES = (
    "章節安排如下",
    "章节安排如下",
    "章節安排",
    "章节安排",
    "chapter outline",
)


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "reading-workspace"


def estimate_tokens(text: str) -> int:
    cjk_chars = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))
    non_cjk_text = re.sub(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", " ", text)
    if not text.strip():
        return 0
    return max(1, int(cjk_chars + len(non_cjk_text.split()) / WORDS_PER_TOKEN))


CHAPTER_PATTERNS = [
    re.compile(
        r"^\s*(?:#{1,6}\s*)?(chapter|ch\.?|cap[ií]tulo)\s+(\d{1,3})\b[:.\-\s]*(.*)$", re.IGNORECASE
    ),
    re.compile(r"^\s*(?:#{1,6}\s*)?(\d{1,2})[.)]\s+([A-Z][^\n]{3,100})$"),
    re.compile(
        r"^\s*(?:#{1,6}\s*)?第\s*([零〇一二两三四五六七八九十百\d]{1,8})\s*[章节篇]\s*[，,：:.\-\s]*(.*)$"
    ),
    re.compile(r"^\s*(?:#{1,6}\s*)?([一二三四五六七八九十]{1,4})[、.．]\s*(.{2,80})$"),
    re.compile(r"^\s*(?:#{1,6}\s*)?([IVXLCDM]{1,8})[.)]\s+([^\n]{3,100})$", re.IGNORECASE),
    re.compile(r"^\s*(?:#{1,6}\s*)?part\s+([IVXLCDM\d]{1,8})\b[:.\-\s]*(.*)$", re.IGNORECASE),
]


@dataclass(frozen=True)
class ChapterCandidate:
    number: int
    title: str
    line: int
    kind: str
    text: str
    in_toc: bool


def chinese_number_to_int(value: str) -> int | None:
    stripped = re.sub(r"\s+", "", value)
    if not stripped:
        return None
    if stripped.isdigit():
        return int(stripped)
    if all(char in CHINESE_DIGITS for char in stripped):
        return int("".join(str(CHINESE_DIGITS[char]) for char in stripped))

    total = 0
    section = 0
    number = 0
    for char in stripped:
        if char in CHINESE_DIGITS:
            number = CHINESE_DIGITS[char]
            continue
        if char == "十":
            section += (number or 1) * 10
            number = 0
            continue
        if char == "百":
            section += (number or 1) * 100
            number = 0
            continue
        return None
    total += section + number
    return total or None


def roman_number_to_int(value: str) -> int | None:
    total = 0
    previous = 0
    for char in reversed(value.upper()):
        current = ROMAN_DIGITS.get(char)
        if current is None:
            return None
        if current < previous:
            total -= current
        else:
            total += current
            previous = current
    return total or None


def normalize_title(title: str, fallback: str) -> str:
    normalized = title.strip(" \t,，:：.-")
    return normalized or fallback


def candidate_kind(pattern: re.Pattern[str]) -> str:
    pattern_index = CHAPTER_PATTERNS.index(pattern)
    if pattern_index in {0, 2, 5}:
        return "formal"
    if pattern_index in {1, 4}:
        return "numbered"
    return "chinese_numbered"


def detect_chapter_match(
    clean: str,
    pattern: re.Pattern[str],
) -> tuple[int, str] | None:
    match = pattern.match(clean)
    if not match:
        return None
    pattern_index = CHAPTER_PATTERNS.index(pattern)
    if pattern_index == 0:
        number = int(match.group(2))
        return number, normalize_title(match.group(3), f"Chapter {number}")
    if pattern_index == 1:
        number = int(match.group(1))
        return number, normalize_title(match.group(2), f"Chapter {number}")
    if pattern_index in {2, 3}:
        number = chinese_number_to_int(match.group(1))
        if number is None:
            return None
        return number, normalize_title(match.group(2), f"Chapter {number}")
    if pattern_index == 4:
        number = roman_number_to_int(match.group(1))
        if number is None:
            return None
        return number, normalize_title(match.group(2), f"Chapter {number}")
    if pattern_index == 5:
        raw_number = match.group(1)
        number = int(raw_number) if raw_number.isdigit() else roman_number_to_int(raw_number)
        if number is None:
            return None
        return number, normalize_title(match.group(2), f"Part {number}")
    return None


def is_heading_like_line(clean: str) -> bool:
    if not clean:
        return False
    if any(detect_chapter_match(clean, pattern) for pattern in CHAPTER_PATTERNS):
        return True
    if len(clean) <= 36 and not re.search(r"[。！？.!?]$", clean):
        return True
    return False


def is_toc_marker(clean: str) -> bool:
    normalized = clean.strip().casefold()
    return normalized in TOC_MARKERS or any(phrase in normalized for phrase in TOC_PHRASES)


def toc_line_numbers(lines: list[str]) -> set[int]:
    toc_lines: set[int] = set()
    for index, line in enumerate(lines):
        clean = line.strip()
        if not is_toc_marker(clean):
            continue
        candidate_seen = 0
        for cursor in range(index + 1, min(len(lines), index + 180)):
            current = lines[cursor].strip()
            if not current:
                toc_lines.add(cursor + 1)
                continue
            if not is_heading_like_line(current) and candidate_seen >= 2:
                break
            if any(detect_chapter_match(current, pattern) for pattern in CHAPTER_PATTERNS):
                candidate_seen += 1
            toc_lines.add(cursor + 1)
    return toc_lines


def chapter_candidates(text: str) -> list[ChapterCandidate]:
    lines = text.splitlines()
    toc_lines = toc_line_numbers(lines)
    candidates: list[ChapterCandidate] = []
    for idx, line in enumerate(lines, start=1):
        clean = line.strip()
        if len(clean) > 140:
            continue
        for pattern in CHAPTER_PATTERNS:
            chapter_match = detect_chapter_match(clean, pattern)
            if not chapter_match:
                continue
            number, title = chapter_match
            if number < 1 or number > 999:
                continue
            kind = candidate_kind(pattern)
            if kind == "numbered" and number > 50:
                continue
            if kind == "numbered" and re.search(r",\s*\d{4}\.?$", clean):
                continue
            candidates.append(
                ChapterCandidate(
                    number=number,
                    title=title,
                    line=idx,
                    kind=kind,
                    text=clean,
                    in_toc=idx in toc_lines,
                )
            )
            break
    return candidates


def first_toc_child(
    candidates: list[ChapterCandidate],
    parent_index: int,
) -> ChapterCandidate | None:
    parent = candidates[parent_index]
    for candidate in candidates[parent_index + 1 :]:
        if candidate.in_toc and candidate.kind == "formal" and candidate.number != parent.number:
            return None
        if candidate.in_toc and candidate.kind == "chinese_numbered":
            return candidate
    return None


def relocated_toc_candidates(
    candidates: list[ChapterCandidate],
) -> list[ChapterCandidate]:
    relocated: list[ChapterCandidate] = []
    body_text_to_line = {
        candidate.text: candidate.line
        for candidate in candidates
        if not candidate.in_toc and candidate.kind == "chinese_numbered"
    }
    for index, candidate in enumerate(candidates):
        if not candidate.in_toc or candidate.kind != "formal":
            continue
        child = first_toc_child(candidates, index)
        if child is None:
            continue
        body_line = body_text_to_line.get(child.text)
        if body_line is None:
            continue
        relocated.append(
            ChapterCandidate(
                number=candidate.number,
                title=candidate.title,
                line=body_line,
                kind="formal",
                text=candidate.text,
                in_toc=False,
            )
        )
    return relocated


def deduplicate_candidates(candidates: list[ChapterCandidate]) -> list[dict[str, object]]:
    chapters: list[dict[str, object]] = []
    seen: set[str] = set()
    for candidate in sorted(candidates, key=lambda item: item.line):
        key = f"ch{candidate.number:02d}"
        if key in seen:
            continue
        seen.add(key)
        chapters.append({"id": key, "title": candidate.title, "line": candidate.line})
    return chapters


def detect_chapters(text: str) -> list[dict[str, object]]:
    candidates = chapter_candidates(text)
    body_formal = [
        candidate
        for candidate in candidates
        if not candidate.in_toc and candidate.kind in {"formal", "numbered"}
    ]
    if body_formal:
        chapters = deduplicate_candidates(body_formal)
    else:
        relocated = relocated_toc_candidates(candidates)
        if relocated:
            chapters = deduplicate_candidates(relocated)
        else:
            fallback = [
                candidate
                for candidate in candidates
                if not candidate.in_toc and candidate.kind == "chinese_numbered"
            ]
            chapters = deduplicate_candidates(fallback)
    if not chapters:
        chapters.append({"id": "ch01", "title": "Full Text", "line": 1})
    return chapters[:120]
