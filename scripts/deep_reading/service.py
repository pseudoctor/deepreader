"""Structured service layer for future web and desktop app integrations."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import ExtractionError
from .llm import build_provider
from .notes import append_text, append_to_section, chapter_note_path, ensure_workspace
from .obsidian import export_obsidian_files
from .reader import get_chapter, get_chapter_text, load_metadata
from .state import load_state
from .workspace import write

ALLOWED_STATES = {"not-started", "reading", "done", "review"}
ALLOWED_NOTE_TYPES = {"Quote", "My Thought", "AI Explanation", "Question"}


def chapter_summary(chapter: dict[str, object], state_value: str) -> dict[str, object]:
    return {
        "id": chapter["id"],
        "title": chapter["title"],
        "state": state_value,
    }


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
        "continue_reading": build_continue_reading(metadata, state),
        "artifacts": {artifact: (workspace / artifact).exists() for artifact in artifacts},
    }


def build_continue_reading(
    metadata: dict[str, object],
    state: dict[str, object],
) -> dict[str, object]:
    chapters = metadata.get("chapters", [])
    chapter_states = state.get("chapters", {})
    current_id = state.get("current")
    current_chapter = None
    review_due = []
    first_reading = None
    first_not_started = None

    for chapter in chapters:
        chapter_id = str(chapter["id"])
        state_value = str(chapter_states.get(chapter_id, "not-started"))
        summary = chapter_summary(chapter, state_value)
        if chapter_id == current_id:
            current_chapter = summary
        if state_value == "done":
            review_due.append(summary)
        if state_value == "reading" and first_reading is None:
            first_reading = summary
        if state_value == "not-started" and first_not_started is None:
            first_not_started = summary

    next_action: dict[str, object]
    if current_chapter and current_chapter["state"] == "reading":
        next_action = {
            "kind": "continue_current",
            "chapter_id": current_chapter["id"],
            "title": current_chapter["title"],
        }
    elif review_due:
        next_action = {
            "kind": "review_completed",
            "chapter_id": review_due[0]["id"],
            "title": review_due[0]["title"],
        }
    elif first_reading:
        next_action = {
            "kind": "continue_current",
            "chapter_id": first_reading["id"],
            "title": first_reading["title"],
        }
    elif first_not_started:
        next_action = {
            "kind": "start_next",
            "chapter_id": first_not_started["id"],
            "title": first_not_started["title"],
        }
    else:
        next_action = {"kind": "synthesize_book", "chapter_id": None, "title": None}

    return {
        "current_chapter": current_chapter,
        "review_due": review_due,
        "next_action": next_action,
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


def find_chapter_window(
    metadata: dict[str, object],
    chapter_id: str,
    count: int,
) -> list[dict[str, object]]:
    if count < 1:
        raise ExtractionError("Chapter count must be at least 1")

    chapters = list(metadata.get("chapters", []))
    start_index = next(
        (index for index, chapter in enumerate(chapters) if chapter["id"] == chapter_id),
        None,
    )
    if start_index is None:
        raise ExtractionError(f"Unknown chapter: {chapter_id}")
    return chapters[start_index : start_index + count]


def synthesize_chapter_window(
    workspace: Path,
    start_chapter_id: str,
    count: int = 3,
) -> dict[str, object]:
    metadata = load_metadata(workspace)
    state = load_state(workspace)
    chapters = find_chapter_window(metadata, start_chapter_id, count)
    if not chapters:
        raise ExtractionError("No chapters available for synthesis")

    summaries = [
        chapter_summary(
            chapter,
            str(state.get("chapters", {}).get(chapter["id"], "not-started")),
        )
        for chapter in chapters
    ]
    labels = [f"{chapter['id']}: {chapter['title']}" for chapter in summaries]
    joined_labels = "; ".join(labels)
    return {
        "start_chapter_id": summaries[0]["id"],
        "chapter_count": len(summaries),
        "chapters": summaries,
        "common_question": (
            "What larger problem do these chapters jointly clarify? Use the chapter titles "
            f"as anchors: {joined_labels}."
        ),
        "recurring_concepts": [
            "Repeated terms, examples, places, actors, or mechanisms across the selected chapters.",
            "Concepts that change meaning or become more precise from one chapter to the next.",
        ],
        "argument_progression": (
            "Explain how the author's argument moves from the first selected chapter to the last: "
            "what is introduced, what is tested, and what becomes more constrained?"
        ),
        "open_questions": [
            "Which claim still needs stronger evidence after these chapters?",
            "Where do the chapters leave a conflict, exception, or unexplained mechanism?",
        ],
    }


def build_book_argument_map(workspace: Path) -> dict[str, object]:
    metadata = load_metadata(workspace)
    state = load_state(workspace)
    chapters = [
        chapter_summary(
            chapter,
            str(state.get("chapters", {}).get(chapter["id"], "not-started")),
        )
        for chapter in metadata.get("chapters", [])
    ]
    if not chapters:
        raise ExtractionError("No chapters available for argument map")

    first = chapters[0]
    last = chapters[-1]
    return {
        "chapter_count": len(chapters),
        "chapters": chapters,
        "core_problem": (
            "What central question makes the whole book necessary? Start from "
            f"{first['id']}: {first['title']} and track how later chapters constrain the answer."
        ),
        "core_answer": (
            "State the book's main answer in one paragraph, then separate what the author "
            "claims from what the evidence directly proves."
        ),
        "argument_chain": [
            f"Opening frame: {first['id']}: {first['title']}",
            (
                "Middle development: identify the chapters where the author adds mechanisms, "
                "comparisons, counterexamples, or historical tests."
            ),
            f"Final position: {last['id']}: {last['title']}",
        ],
        "key_evidence": [
            "List the strongest concrete examples, comparisons, dates, places, or source passages.",
            "For each evidence item, name the claim it supports and its confidence level.",
        ],
        "rebuttals_and_limits": [
            "What alternative explanation would challenge the book's main answer?",
            "Which chapters rely on inference rather than direct evidence?",
            "What would a skeptical reader still need to verify?",
        ],
    }


def format_book_argument_map(result: dict[str, object]) -> str:
    def list_items(items: list[object]) -> str:
        return "\n".join(f"- {item}" for item in items)

    chapters = result["chapters"]
    assert isinstance(chapters, list)
    chapter_lines = [
        f"- {chapter['id']}: {chapter['title']} ({chapter['state']})" for chapter in chapters
    ]
    return "\n".join(
        [
            "## Whole-Book Argument Map",
            "",
            "### Chapters",
            "\n".join(chapter_lines),
            "",
            "### Core Problem",
            str(result["core_problem"]),
            "",
            "### Core Answer",
            str(result["core_answer"]),
            "",
            "### Argument Chain",
            list_items(list(result["argument_chain"])),
            "",
            "### Key Evidence",
            list_items(list(result["key_evidence"])),
            "",
            "### Rebuttals And Limits",
            list_items(list(result["rebuttals_and_limits"])),
        ]
    )


def save_book_argument_map(workspace: Path, result: dict[str, object]) -> dict[str, str]:
    ensure_workspace(workspace)
    path = workspace / "argument_maps.md"
    append_text(path, format_book_argument_map(result))
    return {"kind": "book_argument_map", "path": str(path)}


def generate_active_recall(workspace: Path, chapter_id: str) -> dict[str, object]:
    metadata = load_metadata(workspace)
    state = load_state(workspace)
    chapter = get_chapter(workspace, chapter_id)
    state_value = str(state.get("chapters", {}).get(chapter_id, "not-started"))
    title = str(chapter["title"])
    guide = build_reading_guide(chapter_id, title)
    return {
        "chapter_id": chapter_id,
        "title": title,
        "state": state_value,
        "questions": [
            {
                "question": guide["recall_prompt"],
                "answer_hint": (
                    "Name the chapter's main claim, then add one concrete evidence item."
                ),
            },
            {
                "question": guide["core_question"],
                "answer_hint": "State the problem in your own words before checking notes.",
            },
            {
                "question": (
                    f"How does {chapter_id}: {title} move the book's larger argument forward?"
                ),
                "answer_hint": (
                    "Explain the link to the previous or next chapter, not just this chapter alone."
                ),
            },
        ],
        "eligible_for_review": state_value in {"done", "review"},
        "chapter_count": len(metadata.get("chapters", [])),
    }


def save_active_recall_cards(workspace: Path, result: dict[str, object]) -> dict[str, str]:
    ensure_workspace(workspace)
    questions = result.get("questions", [])
    if not isinstance(questions, list) or not questions:
        raise ExtractionError("Active recall result has no questions")

    path = workspace / "review_cards.md"
    lines = [
        "## Active Recall",
        "",
        f"**Chapter** {result.get('chapter_id')}: {result.get('title')}",
        "",
    ]
    for item in questions:
        if not isinstance(item, dict):
            continue
        lines.extend(
            [
                f"- Q: {item.get('question', '')}",
                f"  A: {item.get('answer_hint', '')}",
            ]
        )
    append_text(path, "\n".join(lines))
    return {"kind": "active_recall_cards", "path": str(path)}


def read_chapter(workspace: Path, chapter_id: str) -> dict[str, object]:
    chapter = get_chapter(workspace, chapter_id)
    return {
        "id": chapter["id"],
        "title": chapter["title"],
        "line": chapter["line"],
        "text": get_chapter_text(workspace, chapter_id),
        "reading_guide": build_reading_guide(chapter["id"], chapter["title"]),
    }


def check_feynman_summary(workspace: Path, chapter_id: str, summary: str) -> dict[str, object]:
    chapter = get_chapter(workspace, chapter_id)
    try:
        return build_provider().check_feynman_summary(chapter, summary)
    except (RuntimeError, ValueError) as exc:
        raise ExtractionError(str(exc)) from exc


def explain_selection(workspace: Path, chapter_id: str, selected_text: str) -> dict[str, str]:
    chapter = get_chapter(workspace, chapter_id)
    try:
        return build_provider().explain_selection(chapter, selected_text)
    except (RuntimeError, ValueError) as exc:
        raise ExtractionError(str(exc)) from exc


def generate_selection_review_question(
    workspace: Path,
    chapter_id: str,
    selected_text: str,
) -> dict[str, str]:
    chapter = get_chapter(workspace, chapter_id)
    try:
        return build_provider().generate_selection_review_question(chapter, selected_text)
    except (RuntimeError, ValueError) as exc:
        raise ExtractionError(str(exc)) from exc


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
