"""Workspace creation and filesystem helpers."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .chapters import detect_chapters, estimate_tokens, slugify
from .errors import ExtractionError
from .models import SourceResult
from .sources import extract_source, resolve_sources
from .templates import (
    argument_maps_template,
    book_map_template,
    chapter_note_template,
    concept_map_template,
    evidence_cards_template,
    library_template,
    multi_source_map_template,
    napkin_template,
    personal_insights_template,
    questions_template,
    reading_plan_template,
    review_cards_template,
    sources_template,
    xray_notes_template,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def build_workspace(source: str, workspace: Path, note_language: str = "auto") -> int:
    sources = resolve_sources(source)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "chapter_notes").mkdir(exist_ok=True)
    (workspace / "source_text").mkdir(exist_ok=True)

    extracted: list[SourceResult] = []
    errors = []
    for path in sources:
        try:
            result = extract_source(path)
            if result.text.strip():
                extracted.append(result)
        except ExtractionError as exc:
            errors.append({"file": str(path), "error": str(exc)})

    if not extracted:
        details = "; ".join(
            f"{Path(str(item['file'])).name}: {item['error']}" for item in errors
        )
        if details:
            raise ExtractionError(f"All sources failed extraction. {details}")
        raise ExtractionError("All sources failed extraction.")

    combined_parts = []
    metadata_sources = []
    for result in extracted:
        boundary = (
            f"\n\n{'=' * 80}\n"
            f"SOURCE: {result.path.name}\n"
            f"PATH: {result.path}\n"
            f"METHOD: {result.method}\n"
            f"{'=' * 80}\n\n"
        )
        combined_parts.append(boundary + result.text.strip())
        metadata_sources.append(
            {
                "source_file": str(result.path),
                "filename": result.path.name,
                "method": result.method,
                "pages": result.pages,
                "chars": len(result.text),
                "words": len(result.text.split()),
                "estimated_tokens": estimate_tokens(result.text),
            }
        )

    full_text = "\n".join(combined_parts).strip()
    chapters = detect_chapters(full_text)
    write(workspace / "source_text" / "full_text.txt", full_text)

    metadata = {
        "created": date.today().isoformat(),
        "source_argument": source,
        "total_sources": len(extracted),
        "sources": metadata_sources,
        "errors": errors,
        "chars": len(full_text),
        "words": len(full_text.split()),
        "estimated_tokens": estimate_tokens(full_text),
        "note_language": note_language,
        "chapters_detected": len(chapters),
        "chapters": chapters,
    }
    write(workspace / "metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))

    title = (
        Path(source).expanduser().name
        if Path(source).expanduser().exists()
        else "Reading Workspace"
    )
    write(workspace / "reading-plan.md", reading_plan_template(title, chapters, note_language))
    write(
        workspace / "book_map.md",
        book_map_template(title, chapters, metadata_sources, note_language),
    )
    write(workspace / "questions.md", questions_template(note_language))
    write(workspace / "concept_map.md", concept_map_template(note_language))
    write(workspace / "review_cards.md", review_cards_template(note_language))
    write(workspace / "personal_insights.md", personal_insights_template(note_language))
    write(workspace / "evidence_cards.md", evidence_cards_template(note_language))
    write(workspace / "argument_maps.md", argument_maps_template(note_language))
    write(workspace / "xray_notes.md", xray_notes_template(note_language))
    write(workspace / "napkin.md", napkin_template(note_language))
    write(
        workspace / "multi_source_map.md",
        multi_source_map_template(metadata_sources, note_language),
    )
    write(workspace / "sources.md", sources_template(metadata_sources, errors))
    write(
        workspace / "library.json",
        json.dumps(
            library_template(source, workspace, metadata_sources, note_language),
            indent=2,
            ensure_ascii=False,
        ),
    )
    state = {"current": chapters[0]["id"], "chapters": {c["id"]: "not-started" for c in chapters}}
    write(workspace / "reading_state.json", json.dumps(state, indent=2))

    for chapter in chapters:
        note_path = (
            workspace / "chapter_notes" / f"{chapter['id']}-{slugify(str(chapter['title']))}.md"
        )
        if not note_path.exists():
            write(
                note_path,
                chapter_note_template(str(chapter["id"]), str(chapter["title"]), note_language),
            )

    print(f"Workspace created: {workspace}")
    print(f"Sources processed: {len(extracted)}")
    print(f"Words: {len(full_text.split()):,}")
    print(f"Estimated tokens: ~{estimate_tokens(full_text) // 1000}K")
    print(f"Chapters detected: {len(chapters)}")
    if errors:
        print(f"Warnings: {len(errors)} source(s) skipped")
    return 0


def default_workspace_for(source: str) -> Path:
    p = Path(source).expanduser()
    name = p.stem if p.is_file() else p.name
    if not name:
        name = "reading-workspace"
    return Path.cwd() / f"{slugify(name)}-reading"
