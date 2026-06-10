"""Structured service layer for future web and desktop app integrations."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import ExtractionError
from .notes import append_text, append_to_section, chapter_note_path, ensure_workspace
from .obsidian import export_obsidian_files
from .reader import get_chapter, get_chapter_text, load_metadata
from .state import load_state
from .workspace import write

ALLOWED_STATES = {"not-started", "reading", "done", "review"}
ALLOWED_NOTE_TYPES = {"Quote", "My Thought", "AI Explanation", "Question"}


def list_chapters(workspace: Path) -> list[dict[str, object]]:
    metadata = load_metadata(workspace)
    state = load_state(workspace)
    chapters = []
    for chapter in metadata.get("chapters", []):
        chapter_id = chapter["id"]
        chapters.append(
            {
                "id": chapter_id,
                "title": chapter["title"],
                "line": chapter["line"],
                "state": state.get("chapters", {}).get(chapter_id, "not-started"),
            }
        )
    return chapters


def get_status(workspace: Path) -> dict[str, object]:
    metadata = load_metadata(workspace)
    state = load_state(workspace)
    counts: dict[str, int] = {}
    for value in state.get("chapters", {}).values():
        counts[value] = counts.get(value, 0) + 1

    artifacts = [
        "evidence_cards.md",
        "argument_maps.md",
        "xray_notes.md",
        "napkin.md",
        "multi_source_map.md",
        "sources.md",
        "library.json",
    ]
    return {
        "workspace": str(workspace),
        "sources": metadata.get("total_sources", 0),
        "words": metadata.get("words", 0),
        "estimated_tokens": metadata.get("estimated_tokens", 0),
        "current": state.get("current"),
        "progress": counts,
        "artifacts": {artifact: (workspace / artifact).exists() for artifact in artifacts},
    }


def build_reading_guide(chapter_id: str, title: str) -> dict[str, str]:
    chapter_label = f"{chapter_id}: {title}"
    return {
        "core_question": f"What problem or shift is {chapter_label} trying to clarify?",
        "evidence_to_seek": (
            "What evidence, concrete examples, comparisons, definitions, or causal links "
            "support the chapter's main claim?"
        ),
        "recall_prompt": (
            "After reading, explain the chapter's main claim in 3-5 sentences and name "
            "one piece of evidence that supports it."
        ),
    }


def read_chapter(workspace: Path, chapter_id: str) -> dict[str, object]:
    chapter = get_chapter(workspace, chapter_id)
    return {
        "id": chapter["id"],
        "title": chapter["title"],
        "line": chapter["line"],
        "text": get_chapter_text(workspace, chapter_id),
        "reading_guide": build_reading_guide(chapter["id"], chapter["title"]),
    }


def update_reading_state(workspace: Path, chapter_id: str, state_value: str) -> dict[str, str]:
    if state_value not in ALLOWED_STATES:
        raise ExtractionError(
            f"Invalid state '{state_value}'. Use one of: {', '.join(sorted(ALLOWED_STATES))}"
        )

    state = load_state(workspace)
    if chapter_id not in state.get("chapters", {}):
        raise ExtractionError(f"Unknown chapter: {chapter_id}")

    state["chapters"][chapter_id] = state_value
    state["current"] = chapter_id
    write(workspace / "reading_state.json", json.dumps(state, indent=2))
    return {"chapter_id": chapter_id, "state": state_value, "current": chapter_id}


def format_typed_note(note_type: str, text: str) -> str:
    if note_type == "Quote":
        return "> " + text.strip().replace("\n", "\n> ")
    return text.strip()


def add_note(
    workspace: Path,
    chapter_id: str,
    section: str,
    text: str,
    note_type: str = "My Thought",
) -> dict[str, str]:
    if note_type not in ALLOWED_NOTE_TYPES:
        raise ExtractionError(
            f"Invalid note type '{note_type}'. Use one of: {', '.join(sorted(ALLOWED_NOTE_TYPES))}"
        )

    path = chapter_note_path(workspace, chapter_id)
    append_to_section(path, section, format_typed_note(note_type, text), note_type)
    return {
        "kind": "chapter_note",
        "chapter_id": chapter_id,
        "section": section,
        "note_type": note_type,
        "path": str(path),
    }


def add_quote(workspace: Path, chapter_id: str, quote: str, locator: str) -> dict[str, str]:
    path = chapter_note_path(workspace, chapter_id)
    append_text(
        path,
        "\n".join(
            [
                "## Quote",
                "",
                f"**Locator** {locator}",
                "",
                "> " + quote.strip().replace("\n", "\n> "),
            ]
        ),
    )
    return {
        "kind": "quote",
        "chapter_id": chapter_id,
        "locator": locator,
        "path": str(path),
    }


def add_insight(workspace: Path, text: str) -> dict[str, str]:
    ensure_workspace(workspace)
    path = workspace / "personal_insights.md"
    append_to_section(path, "Ideas To Apply", text)
    return {"kind": "insight", "path": str(path)}


def add_review_card(workspace: Path, question: str, answer: str) -> dict[str, str]:
    ensure_workspace(workspace)
    path = workspace / "review_cards.md"
    append_text(path, f"- Q: {question}\n  A: {answer}")
    return {"kind": "review_card", "path": str(path)}


def add_evidence_card(
    workspace: Path,
    claim: str,
    locator: str,
    support: str,
    confidence: str,
    not_explicit: str = "TBD",
    inference: str = "TBD",
) -> dict[str, str]:
    ensure_workspace(workspace)
    path = workspace / "evidence_cards.md"
    append_text(
        path,
        "\n".join(
            [
                "## Evidence Card",
                "",
                f"**Claim** {claim}",
                "",
                "**Source Locator**",
                f"- {locator}",
                "",
                f"**Support** {support}",
                "",
                f"**Confidence** {confidence}",
                "",
                f"**Not Explicit / Needs Verification** {not_explicit}",
                "",
                f"**My Inference** {inference}",
            ]
        ),
    )
    return {"kind": "evidence_card", "path": str(path)}


def export_obsidian(workspace: Path, vault_folder: Path) -> dict[str, object]:
    return export_obsidian_files(workspace, vault_folder)
