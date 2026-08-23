"""Read chapter text from a workspace."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import ExtractionError


def load_metadata(workspace: Path) -> dict:
    metadata_path = workspace / "metadata.json"
    if not metadata_path.exists():
        raise ExtractionError(f"Missing metadata.json in {workspace}")
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"Invalid metadata.json in {workspace}") from exc
    if not isinstance(data, dict):
        raise ExtractionError(f"Invalid metadata.json in {workspace}")
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise ExtractionError(f"Invalid chapters in metadata.json in {workspace}")
    seen_ids: set[str] = set()
    previous_line = 0
    for chapter in chapters:
        if not isinstance(chapter, dict):
            raise ExtractionError(f"Invalid chapters in metadata.json in {workspace}")
        chapter_id = chapter.get("id")
        title = chapter.get("title")
        line = chapter.get("line")
        if (
            not isinstance(chapter_id, str)
            or not chapter_id.strip()
            or chapter_id in seen_ids
            or not isinstance(title, str)
            or not title.strip()
            or not isinstance(line, int)
            or isinstance(line, bool)
            or line <= previous_line
        ):
            raise ExtractionError(f"Invalid chapters in metadata.json in {workspace}")
        seen_ids.add(chapter_id)
        previous_line = line
    return data


def load_full_text(workspace: Path) -> list[str]:
    full_text_path = workspace / "source_text" / "full_text.txt"
    if not full_text_path.exists():
        raise ExtractionError(f"Missing source_text/full_text.txt in {workspace}")
    return full_text_path.read_text(encoding="utf-8").splitlines()


def get_chapter(workspace: Path, chapter_id: str) -> dict[str, object]:
    metadata = load_metadata(workspace)
    chapters = metadata.get("chapters", [])
    for chapter in chapters:
        if chapter.get("id") == chapter_id:
            return chapter
    raise ExtractionError(f"Unknown chapter: {chapter_id}")


def get_chapter_text(workspace: Path, chapter_id: str) -> str:
    metadata = load_metadata(workspace)
    full_text_lines = load_full_text(workspace)
    chapters = metadata.get("chapters", [])
    current_index = None

    for index, chapter in enumerate(chapters):
        if chapter.get("id") == chapter_id:
            current_index = index
            break

    if current_index is None:
        raise ExtractionError(f"Unknown chapter: {chapter_id}")

    chapter = chapters[current_index]
    try:
        start_line = int(chapter["line"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ExtractionError(f"Invalid chapter line for {chapter_id}") from exc

    if start_line < 1 or start_line > len(full_text_lines):
        raise ExtractionError(f"Chapter line out of range for {chapter_id}: {start_line}")

    next_line = len(full_text_lines) + 1
    if current_index + 1 < len(chapters):
        try:
            next_line = int(chapters[current_index + 1]["line"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ExtractionError(f"Invalid next chapter line after {chapter_id}") from exc

    if next_line <= start_line:
        raise ExtractionError(f"Invalid chapter range for {chapter_id}")

    return "\n".join(full_text_lines[start_line - 1 : next_line - 1]).strip()


def cmd_chapter_text(workspace: Path, chapter_id: str) -> int:
    print(get_chapter_text(workspace, chapter_id))
    return 0
