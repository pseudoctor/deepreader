"""Structured service layer for future web and desktop app integrations."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import ExtractionError
from .notes import append_text, append_to_section, chapter_note_path, ensure_workspace
from .obsidian import export_obsidian_files
from .reader import get_chapter, get_chapter_text, load_metadata
from .state import load_state
from .workspace import write

ALLOWED_STATES = {"not-started", "reading", "done", "review"}
ALLOWED_NOTE_TYPES = {"Quote", "My Thought", "AI Explanation", "Question"}
CAUSAL_MARKERS = (
    "because",
    "therefore",
    "so",
    "since",
    "leads to",
    "causes",
    "因",
    "所以",
    "导致",
)
EVIDENCE_MARKERS = (
    "evidence",
    "example",
    "for example",
    "according",
    "quote",
    "原文",
    "证据",
    "例如",
)
VAGUE_MARKERS = ("things", "stuff", "important", "interesting", "很多", "一些", "重要", "有趣")


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


def read_chapter(workspace: Path, chapter_id: str) -> dict[str, object]:
    chapter = get_chapter(workspace, chapter_id)
    return {
        "id": chapter["id"],
        "title": chapter["title"],
        "line": chapter["line"],
        "text": get_chapter_text(workspace, chapter_id),
        "reading_guide": build_reading_guide(chapter["id"], chapter["title"]),
    }


def split_summary_sentences(summary: str) -> list[str]:
    normalized = summary.replace("。", ".").replace("？", "?").replace("！", "!")
    sentences = []
    for chunk in normalized.replace("?", ".").replace("!", ".").split("."):
        sentence = chunk.strip()
        if sentence:
            sentences.append(sentence)
    return sentences


def contains_marker(text: str, marker: str) -> bool:
    if marker.isascii():
        return re.search(rf"\b{re.escape(marker)}\b", text) is not None
    return marker in text


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def check_feynman_summary(workspace: Path, chapter_id: str, summary: str) -> dict[str, object]:
    chapter = get_chapter(workspace, chapter_id)
    stripped = summary.strip()
    if not stripped:
        raise ExtractionError("Summary cannot be empty")

    lowered = stripped.casefold()
    sentences = split_summary_sentences(stripped)
    accurate_points = [
        sentence
        for sentence in sentences
        if len(sentence) >= 40
        and not any(contains_marker(sentence.casefold(), marker) for marker in VAGUE_MARKERS)
    ]
    vague_points = [
        sentence
        for sentence in sentences
        if len(sentence) < 40
        or any(contains_marker(sentence.casefold(), marker) for marker in VAGUE_MARKERS)
    ]
    missing_causal_links = []
    if not any(contains_marker(lowered, marker) for marker in CAUSAL_MARKERS):
        missing_causal_links.append(
            "The summary does not clearly explain the causal link or mechanism."
        )

    unsupported_leaps = []
    if not any(contains_marker(lowered, marker) for marker in EVIDENCE_MARKERS):
        unsupported_leaps.append("The summary does not name a concrete example or evidence.")

    rewritten_version = (
        f"In {chapter['id']}: {chapter['title']}, the chapter appears to argue that "
        f"{sentences[0] if sentences else stripped}. To make the explanation stronger, add the "
        "causal mechanism and one concrete piece of evidence from the text."
    )
    return {
        "chapter_id": chapter["id"],
        "title": chapter["title"],
        "accurate_points": accurate_points,
        "vague_points": vague_points,
        "missing_causal_links": missing_causal_links,
        "unsupported_leaps": unsupported_leaps,
        "rewritten_version": rewritten_version,
    }


def explain_selection(workspace: Path, chapter_id: str, selected_text: str) -> dict[str, str]:
    chapter = get_chapter(workspace, chapter_id)
    text = selected_text.strip()
    if not text:
        raise ExtractionError("Selected text cannot be empty")

    if contains_cjk(text):
        explanation = "\n".join(
            [
                f"选中文段来自 {chapter['id']}: {chapter['title']}",
                "",
                "它在说什么：",
                text,
                "",
                "怎么读这段：",
                (
                    "先判断这段支持了什么主张，再找它给出的证据，以及暗含的因果链。"
                    "如果它在做比较，就追问：被比较对象之间变了什么，什么又保持不变。"
                ),
            ]
        )
    else:
        explanation = "\n".join(
            [
                f"Selected passage from {chapter['id']}: {chapter['title']}",
                "",
                "What it says:",
                text,
                "",
                "How to read it:",
                (
                    "Identify the claim this passage supports, the evidence it names, and any "
                    "causal link it implies. If the passage uses a comparison, ask what changed "
                    "between the compared cases and what stays constant."
                ),
            ]
        )

    return {
        "chapter_id": chapter["id"],
        "title": chapter["title"],
        "explanation": explanation,
    }


def generate_selection_review_question(
    workspace: Path,
    chapter_id: str,
    selected_text: str,
) -> dict[str, str]:
    chapter = get_chapter(workspace, chapter_id)
    text = selected_text.strip()
    if not text:
        raise ExtractionError("Selected text cannot be empty")

    preview = text if len(text) <= 180 else text[:177].rstrip() + "..."
    if contains_cjk(text):
        return {
            "chapter_id": chapter["id"],
            "title": chapter["title"],
            "question": f"这段文字在 {chapter['id']} 中支持了什么主张或因果链？",
            "answer": (
                f"可用这段作为证据：{preview}\n\n"
                "一个好的回答需要说清楚主张、解释因果链，并指出这段本身还不能证明什么。"
            ),
        }

    return {
        "chapter_id": chapter["id"],
        "title": chapter["title"],
        "question": f"What claim or causal link does this passage support in {chapter['id']}?",
        "answer": (
            f"Use this passage as evidence: {preview}\n\n"
            "A strong answer should name the claim, explain the causal link, and state what "
            "the passage does not prove by itself."
        ),
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
