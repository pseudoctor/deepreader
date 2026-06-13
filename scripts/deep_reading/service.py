"""Structured service layer for future web and desktop app integrations."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import ExtractionError
from .llm import build_provider
from .notes import append_text, append_to_section, chapter_note_path, ensure_workspace
from .obsidian import export_obsidian_files
from .reader import get_chapter, get_chapter_text, load_metadata
from .state import load_state
from .workspace import write

ALLOWED_STATES = {"not-started", "reading", "done", "review", "weak"}
ALLOWED_NOTE_TYPES = {"Quote", "My Thought", "AI Explanation", "Question"}
LEARNING_LOOP_FILE = "learning_loop.json"


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
        "learning_loop": build_learning_loop(workspace, metadata, state),
        "artifacts": {artifact: (workspace / artifact).exists() for artifact in artifacts},
    }


def read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_learning_loop_state(workspace: Path) -> dict[str, object]:
    path = workspace / LEARNING_LOOP_FILE
    if not path.exists():
        return {"weak_concepts": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ExtractionError(f"Invalid {LEARNING_LOOP_FILE}")
    weak_concepts = data.get("weak_concepts", [])
    if not isinstance(weak_concepts, list):
        raise ExtractionError(f"Invalid weak_concepts in {LEARNING_LOOP_FILE}")
    return {"weak_concepts": weak_concepts}


def save_learning_loop_state(workspace: Path, data: dict[str, object]) -> None:
    ensure_workspace(workspace)
    write(workspace / LEARNING_LOOP_FILE, json.dumps(data, indent=2, ensure_ascii=False))


def add_weak_concept(
    workspace: Path,
    concept: str,
    chapter_id: str,
    note: str = "",
) -> dict[str, object]:
    stripped_concept = concept.strip()
    stripped_note = note.strip()
    if not stripped_concept:
        raise ExtractionError("Weak concept cannot be empty")

    chapter = get_chapter(workspace, chapter_id)
    data = load_learning_loop_state(workspace)
    weak_concepts = list(data.get("weak_concepts", []))
    next_item = {
        "concept": stripped_concept,
        "chapter_id": chapter["id"],
        "title": chapter["title"],
        "note": stripped_note,
    }
    weak_concepts = [
        item
        for item in weak_concepts
        if not (
            isinstance(item, dict)
            and item.get("concept") == stripped_concept
            and item.get("chapter_id") == chapter["id"]
        )
    ]
    weak_concepts.insert(0, next_item)
    save_learning_loop_state(workspace, {"weak_concepts": weak_concepts})
    return {"kind": "weak_concept", **next_item}


def chapter_has_notes(workspace: Path, chapter_id: str) -> bool:
    try:
        content = chapter_note_path(workspace, chapter_id).read_text(encoding="utf-8")
    except ExtractionError:
        return False
    return "\n### " in content or "\n## Quote\n" in content


def chapter_has_active_recall(workspace: Path, chapter_id: str) -> bool:
    content = read_text_if_exists(workspace / "review_cards.md")
    return f"**Chapter** {chapter_id}:" in content


def chapter_has_evidence(workspace: Path, chapter_id: str) -> bool:
    content = read_text_if_exists(workspace / "evidence_cards.md")
    return chapter_id in content


def chapter_mastery(
    workspace: Path,
    chapter: dict[str, object],
    state_value: str,
) -> dict[str, object]:
    chapter_id = str(chapter["id"])
    has_notes = chapter_has_notes(workspace, chapter_id)
    has_recall = chapter_has_active_recall(workspace, chapter_id)
    has_evidence = chapter_has_evidence(workspace, chapter_id)
    state_scores = {
        "not-started": 0,
        "reading": 20,
        "weak": 30,
        "done": 50,
        "review": 70,
    }
    score = state_scores.get(state_value, 0)
    if has_notes:
        score += 10
    if has_recall:
        score += 12
    if has_evidence:
        score += 8
    score = min(score, 100)

    reasons = []
    if state_value == "weak":
        reasons.append("Marked weak")
    if state_value == "done" and not has_recall:
        reasons.append("Done but active recall not saved")
    if state_value in {"done", "review", "weak"} and not has_notes:
        reasons.append("No chapter note activity")
    if state_value in {"done", "review", "weak"} and not has_evidence:
        reasons.append("No evidence card linked")
    if score < 60 and state_value != "not-started":
        reasons.append("Mastery score below 60")

    return {
        "id": chapter_id,
        "title": chapter["title"],
        "state": state_value,
        "mastery_score": score,
        "has_notes": has_notes,
        "has_active_recall": has_recall,
        "has_evidence": has_evidence,
        "weak_reasons": reasons,
    }


def build_learning_loop(
    workspace: Path,
    metadata: dict[str, object],
    state: dict[str, object],
) -> dict[str, object]:
    chapter_states = state.get("chapters", {})
    chapters = [
        chapter_mastery(
            workspace,
            chapter,
            str(chapter_states.get(chapter["id"], "not-started")),
        )
        for chapter in metadata.get("chapters", [])
    ]
    weak_chapters = [
        chapter
        for chapter in chapters
        if chapter["state"] == "weak"
        or (chapter["state"] in {"done", "review"} and int(chapter["mastery_score"]) < 70)
    ]
    weak_chapters.sort(key=lambda chapter: int(chapter["mastery_score"]))
    review_ready = [chapter for chapter in chapters if chapter["state"] in {"done", "weak"}]
    completed_count = sum(1 for chapter in chapters if chapter["state"] in {"done", "review"})
    loop_state = load_learning_loop_state(workspace)
    return {
        "chapters": chapters,
        "weak_chapters": weak_chapters,
        "weak_concepts": loop_state["weak_concepts"],
        "review_ready": review_ready,
        "synthesis_due": completed_count >= 3 and completed_count % 3 == 0,
        "completed_count": completed_count,
        "average_mastery": (
            round(sum(int(chapter["mastery_score"]) for chapter in chapters) / len(chapters))
            if chapters
            else 0
        ),
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
        if state_value in {"done", "weak"}:
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


def clean_chapter_sentences(text: str) -> list[str]:
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^chapter\s*\d+\b", stripped, flags=re.IGNORECASE):
            continue
        cleaned_lines.append(stripped)
    cleaned_text = " ".join(cleaned_lines)
    chunks = re.split(r"(?<=[.!?。！？])\s*", cleaned_text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def build_reading_guide(chapter_id: str, title: str, text: str = "") -> dict[str, str]:
    chapter_label = f"{chapter_id}: {title}"
    sentences = clean_chapter_sentences(text)
    first_sentence = sentences[0] if sentences else ""
    use_chinese = contains_cjk(f"{title}\n{text}")
    question_sentence = next(
        (sentence for sentence in sentences if "?" in sentence or "？" in sentence),
        "",
    )
    causal_sentence = next(
        (
            sentence
            for sentence in sentences
            if any(
                marker in sentence.casefold()
                for marker in (
                    "because",
                    "therefore",
                    "causes",
                    "leads to",
                    "why",
                    "因",
                    "所以",
                    "导致",
                )
            )
        ),
        "",
    )

    if first_sentence:
        focus = question_sentence or first_sentence
        evidence_focus = causal_sentence or first_sentence
        if use_chinese:
            return {
                "core_question": (
                    f"阅读 {chapter_label} 时，先想清楚它要你解释"
                    f"“{focus[:120]}”里的什么问题？"
                ),
                "evidence_to_seek": (
                    "寻找支撑这一段的具体证据、比较、定义或因果链："
                    f"“{evidence_focus[:120]}”。"
                ),
                "recall_prompt": (
                    f"读完 {chapter_label} 后，用 3-5 句话复述本章主张，"
                    "并写出一个改变你理解的例子。"
                ),
            }
        return {
            "core_question": (
                f"What is {chapter_label} asking you to explain about \"{focus[:120]}\"?"
            ),
            "evidence_to_seek": (
                "Find the concrete evidence, comparison, definition, or causal link behind "
                f"\"{evidence_focus[:120]}\"."
            ),
            "recall_prompt": (
                f"After reading {chapter_label}, explain the main claim in 3-5 sentences "
                "and cite one example that changed your view."
            ),
        }

    if use_chinese:
        return {
            "core_question": f"{chapter_label} 想澄清什么问题、变化或矛盾？",
            "evidence_to_seek": "哪些证据、具体例子、比较、定义或因果链支撑了本章的核心主张？",
            "recall_prompt": "读完后，用 3-5 句话复述本章主张，并指出一个支撑它的证据。",
        }

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


def extract_evidence_lines(workspace: Path, limit: int = 5) -> list[str]:
    content = read_text_if_exists(workspace / "evidence_cards.md")
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("**Claim**") or stripped.startswith("**Support**"):
            lines.append(stripped.replace("**", ""))
        if len(lines) >= limit:
            break
    return lines


def build_one_page_book_account(workspace: Path) -> dict[str, object]:
    metadata = load_metadata(workspace)
    state = load_state(workspace)
    learning_loop = build_learning_loop(workspace, metadata, state)
    chapters = learning_loop["chapters"]
    assert isinstance(chapters, list)
    if not chapters:
        raise ExtractionError("No chapters available for one-page account")

    chapter_labels = [
        f"{chapter['id']}: {chapter['title']} ({chapter['state']}, {chapter['mastery_score']}%)"
        for chapter in chapters
    ]
    weak_concepts = learning_loop["weak_concepts"]
    assert isinstance(weak_concepts, list)
    weak_points = [
        f"{item.get('concept')} in {item.get('chapter_id')}: {item.get('note')}".strip()
        for item in weak_concepts
        if isinstance(item, dict)
    ]
    weak_chapters = learning_loop["weak_chapters"]
    assert isinstance(weak_chapters, list)
    weak_points.extend(
        f"{chapter['id']}: {chapter['title']} needs review because "
        + "; ".join(str(reason) for reason in chapter.get("weak_reasons", []))
        for chapter in weak_chapters
        if isinstance(chapter, dict)
    )

    title = str(metadata.get("title") or workspace.name)
    evidence = extract_evidence_lines(workspace)
    return {
        "title": title,
        "chapter_count": len(chapters),
        "completed_count": learning_loop["completed_count"],
        "average_mastery": learning_loop["average_mastery"],
        "core_account": (
            f"{title} currently has {len(chapters)} detected chapters. The grounded account "
            "should explain the central problem by moving from the opening chapters through "
            "the strongest completed or reviewed chapters, while separating direct evidence "
            "from the reader's inference."
        ),
        "core_argument_chain": [
            "Opening frame: " + str(chapter_labels[0]),
            (
                "Development: compare how later chapters add mechanisms, evidence, "
                "exceptions, or scope."
            ),
            "Current endpoint: " + str(chapter_labels[-1]),
        ],
        "strongest_evidence": evidence
        or [
            (
                "No evidence cards have been saved yet; add evidence cards before treating "
                "this account as grounded."
            )
        ],
        "weak_points": weak_points
        or ["No weak concepts or weak chapters have been recorded yet."],
        "application_prompts": [
            "What decision, project, or research question does this book change?",
            (
                "Which claim is directly supported by evidence, and which part is still "
                "your inference?"
            ),
            "What would you test or look up next before applying the book's argument?",
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


def format_one_page_book_account(result: dict[str, object]) -> str:
    def list_items(items: list[object]) -> str:
        return "\n".join(f"- {item}" for item in items)

    return "\n".join(
        [
            "# One-Page Book Account",
            "",
            f"**Book** {result['title']}",
            f"**Chapters** {result['completed_count']} / {result['chapter_count']} completed",
            f"**Average Mastery** {result['average_mastery']}%",
            "",
            "## Core Account",
            str(result["core_account"]),
            "",
            "## Core Argument Chain",
            list_items(list(result["core_argument_chain"])),
            "",
            "## Strongest Evidence",
            list_items(list(result["strongest_evidence"])),
            "",
            "## Weak Points",
            list_items(list(result["weak_points"])),
            "",
            "## Application Prompts",
            list_items(list(result["application_prompts"])),
        ]
    )


def save_one_page_book_account(workspace: Path, result: dict[str, object]) -> dict[str, str]:
    ensure_workspace(workspace)
    path = workspace / "one_page_account.md"
    write(path, format_one_page_book_account(result) + "\n")
    return {"kind": "one_page_book_account", "path": str(path)}


def strip_markdown_label(line: str, label: str) -> str:
    prefix = f"**{label}**"
    return line.removeprefix(prefix).strip()


def build_evidence_table(workspace: Path) -> dict[str, object]:
    ensure_workspace(workspace)
    content = read_text_if_exists(workspace / "evidence_cards.md")
    cards: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    pending_field: str | None = None

    field_headings = {
        "**Source Locator**": "source_locator",
        "**Support**": "support",
        "**Confidence**": "confidence",
        "**Not Explicit / Needs Verification**": "not_explicit",
        "**My Inference**": "inference",
    }

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line == "## Evidence Card":
            if current:
                cards.append(current)
            current = {
                "claim": "",
                "source_locator": "",
                "support": "",
                "confidence": "",
                "not_explicit": "",
                "inference": "",
            }
            pending_field = None
            continue
        if current is None:
            continue
        if line.startswith("**Claim**"):
            current["claim"] = strip_markdown_label(line, "Claim")
            pending_field = None
            continue
        inline_matched = False
        for heading, field in field_headings.items():
            if line == heading:
                pending_field = field
                inline_matched = True
                break
            if line.startswith(heading):
                current[field] = line.removeprefix(heading).strip()
                pending_field = None
                inline_matched = True
                break
        if inline_matched:
            continue
        if pending_field and line.startswith("- "):
            current[pending_field] = line.removeprefix("- ").strip()

    if current:
        cards.append(current)

    return {
        "card_count": len(cards),
        "cards": cards,
    }


def markdown_table_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def format_evidence_table(result: dict[str, object]) -> str:
    cards = result["cards"]
    assert isinstance(cards, list)
    rows = [
        "| Claim | Source Locator | Support | Confidence | Not Explicit | Inference |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for card in cards:
        assert isinstance(card, dict)
        rows.append(
            "| "
            + " | ".join(
                [
                    markdown_table_cell(card.get("claim", "")),
                    markdown_table_cell(card.get("source_locator", "")),
                    markdown_table_cell(card.get("support", "")),
                    markdown_table_cell(card.get("confidence", "")),
                    markdown_table_cell(card.get("not_explicit", "")),
                    markdown_table_cell(card.get("inference", "")),
                ]
            )
            + " |"
        )
    return "\n".join(["# Evidence Table", "", *rows])


def save_evidence_table(workspace: Path, result: dict[str, object]) -> dict[str, str]:
    ensure_workspace(workspace)
    path = workspace / "evidence_table.md"
    write(path, format_evidence_table(result) + "\n")
    return {"kind": "evidence_table", "path": str(path)}


def build_concept_map(workspace: Path) -> dict[str, object]:
    metadata = load_metadata(workspace)
    state = load_state(workspace)
    learning_loop = build_learning_loop(workspace, metadata, state)
    evidence_table = build_evidence_table(workspace)
    chapters = learning_loop["chapters"]
    weak_concepts = learning_loop["weak_concepts"]
    evidence_cards = evidence_table["cards"]
    assert isinstance(chapters, list)
    assert isinstance(weak_concepts, list)
    assert isinstance(evidence_cards, list)

    nodes: list[dict[str, object]] = []
    links: list[dict[str, str]] = []
    for chapter in chapters:
        assert isinstance(chapter, dict)
        nodes.append(
            {
                "id": str(chapter["id"]),
                "label": f"{chapter['id']}: {chapter['title']}",
                "type": "chapter",
                "state": str(chapter["state"]),
                "mastery_score": int(chapter["mastery_score"]),
            }
        )

    for previous, current in zip(chapters, chapters[1:], strict=False):
        assert isinstance(previous, dict)
        assert isinstance(current, dict)
        links.append(
            {
                "source": str(previous["id"]),
                "target": str(current["id"]),
                "relation": "progresses_to",
                "evidence": "chapter order",
            }
        )

    for item in weak_concepts:
        if not isinstance(item, dict):
            continue
        concept = str(item.get("concept", "")).strip()
        chapter_id = str(item.get("chapter_id", "")).strip()
        if not concept or not chapter_id:
            continue
        node_id = f"weak:{chapter_id}:{concept}"
        nodes.append(
            {
                "id": node_id,
                "label": concept,
                "type": "weak_concept",
                "state": "weak",
                "mastery_score": 0,
            }
        )
        links.append(
            {
                "source": node_id,
                "target": chapter_id,
                "relation": "unclear_in",
                "evidence": str(item.get("note", "")).strip() or "manual weak concept",
            }
        )

    for index, card in enumerate(evidence_cards, start=1):
        if not isinstance(card, dict):
            continue
        claim = str(card.get("claim", "")).strip()
        locator = str(card.get("source_locator", "")).strip()
        support = str(card.get("support", "")).strip()
        if not claim:
            continue
        node_id = f"evidence:{index}"
        nodes.append(
            {
                "id": node_id,
                "label": claim,
                "type": "evidence",
                "state": str(card.get("confidence", "")),
                "mastery_score": 0,
            }
        )
        target = next(
            (
                str(chapter["id"])
                for chapter in chapters
                if isinstance(chapter, dict) and str(chapter["id"]) in locator
            ),
            str(chapters[0]["id"]) if chapters and isinstance(chapters[0], dict) else "",
        )
        if target:
            links.append(
                {
                    "source": node_id,
                    "target": target,
                    "relation": "supports",
                    "evidence": support or locator or "evidence card",
                }
            )

    return {
        "node_count": len(nodes),
        "link_count": len(links),
        "nodes": nodes,
        "links": links,
    }


def format_concept_map(result: dict[str, object]) -> str:
    nodes = result["nodes"]
    links = result["links"]
    assert isinstance(nodes, list)
    assert isinstance(links, list)
    lines = ["# Concept Map", "", "## Nodes"]
    for node in nodes:
        assert isinstance(node, dict)
        lines.append(
            f"- **{node.get('label', '')}** "
            f"({node.get('type', '')}; mastery {node.get('mastery_score', 0)}%)"
        )
    lines.extend(["", "## Links"])
    for link in links:
        assert isinstance(link, dict)
        lines.append(
            f"- {link.get('source', '')} --{link.get('relation', '')}-> "
            f"{link.get('target', '')}: {link.get('evidence', '')}"
        )
    return "\n".join(lines)


def save_concept_map(workspace: Path, result: dict[str, object]) -> dict[str, str]:
    ensure_workspace(workspace)
    path = workspace / "concept_map.md"
    write(path, format_concept_map(result) + "\n")
    return {"kind": "concept_map", "path": str(path)}


def tokenize_query(query: str) -> list[str]:
    return [
        token.casefold()
        for token in re.findall(r"[\w'-]+|[\u4e00-\u9fff]+", query)
        if len(token.strip()) >= 2
    ]


def compact_snippet(text: str, limit: int = 420) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def evidence_context_score(text: str, query: str, tokens: list[str]) -> int:
    lowered = text.casefold()
    score = 0
    stripped_query = query.casefold().strip()
    if stripped_query and stripped_query in lowered:
        score += 8
    for token in tokens:
        score += lowered.count(token)
    return score


def add_evidence_context_candidate(
    matches: list[dict[str, object]],
    *,
    source_type: str,
    locator: str,
    text: str,
    query: str,
    tokens: list[str],
    chapter_id: str | None = None,
    title: str | None = None,
) -> None:
    score = evidence_context_score(text, query, tokens)
    if score <= 0:
        return
    matches.append(
        {
            "source_type": source_type,
            "locator": locator,
            "chapter_id": chapter_id,
            "title": title,
            "snippet": compact_snippet(text),
            "score": score,
        }
    )


def chapter_context_candidates(
    workspace: Path,
    query: str,
    tokens: list[str],
    chapter_id: str | None,
) -> list[dict[str, object]]:
    metadata = load_metadata(workspace)
    chapters = metadata.get("chapters", [])
    if chapter_id is not None:
        get_chapter(workspace, chapter_id)

    matches: list[dict[str, object]] = []
    for chapter in chapters:
        current_id = str(chapter["id"])
        if chapter_id is not None and current_id != chapter_id:
            continue
        text = get_chapter_text(workspace, current_id)
        chunks = [
            chunk.strip()
            for chunk in re.split(r"\n\s*\n|(?<=[.!?。！？])\s+", text)
            if chunk.strip()
        ]
        for chunk in chunks:
            add_evidence_context_candidate(
                matches,
                source_type="chapter",
                locator=f"{current_id}: {chapter['title']}",
                chapter_id=current_id,
                title=str(chapter["title"]),
                text=chunk,
                query=query,
                tokens=tokens,
            )
    return matches


def evidence_card_context_candidates(
    workspace: Path,
    query: str,
    tokens: list[str],
    chapter_id: str | None,
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    table = build_evidence_table(workspace)
    for card in table["cards"]:
        if not isinstance(card, dict):
            continue
        locator = str(card.get("source_locator", "")).strip()
        if chapter_id is not None and chapter_id not in locator:
            continue
        text = " ".join(
            str(card.get(field, "")).strip()
            for field in ("claim", "support", "not_explicit", "inference")
            if str(card.get(field, "")).strip()
        )
        add_evidence_context_candidate(
            matches,
            source_type="evidence_card",
            locator=locator or "evidence_cards.md",
            chapter_id=chapter_id,
            title=None,
            text=text,
            query=query,
            tokens=tokens,
        )
    return matches


def chapter_note_context_candidates(
    workspace: Path,
    query: str,
    tokens: list[str],
    chapter_id: str | None,
) -> list[dict[str, object]]:
    metadata = load_metadata(workspace)
    matches: list[dict[str, object]] = []
    for chapter in metadata.get("chapters", []):
        current_id = str(chapter["id"])
        if chapter_id is not None and current_id != chapter_id:
            continue
        path = chapter_note_path(workspace, current_id)
        if not path.exists():
            continue
        chunks = [
            chunk.strip()
            for chunk in re.split(r"\n(?=##+ )|\n\s*\n", path.read_text(encoding="utf-8"))
            if chunk.strip()
        ]
        for chunk in chunks:
            add_evidence_context_candidate(
                matches,
                source_type="chapter_note",
                locator=f"{current_id}: {chapter['title']} note",
                chapter_id=current_id,
                title=str(chapter["title"]),
                text=chunk,
                query=query,
                tokens=tokens,
            )
    return matches


def build_evidence_context(
    workspace: Path,
    query: str,
    chapter_id: str | None = None,
    limit: int = 5,
) -> dict[str, object]:
    ensure_workspace(workspace)
    stripped_query = query.strip()
    if not stripped_query:
        raise ExtractionError("Evidence context query cannot be empty")
    if limit < 1:
        raise ExtractionError("Evidence context limit must be at least 1")

    tokens = tokenize_query(stripped_query)
    if not tokens:
        tokens = [stripped_query.casefold()]
    safe_limit = min(limit, 20)
    matches: list[dict[str, object]] = []
    matches.extend(chapter_context_candidates(workspace, stripped_query, tokens, chapter_id))
    matches.extend(evidence_card_context_candidates(workspace, stripped_query, tokens, chapter_id))
    matches.extend(chapter_note_context_candidates(workspace, stripped_query, tokens, chapter_id))
    matches.sort(
        key=lambda item: (
            -int(item["score"]),
            str(item["source_type"]),
            str(item["locator"]),
        )
    )
    return {
        "query": stripped_query,
        "matches": matches[:safe_limit],
    }


def format_evidence_context(result: dict[str, object]) -> str:
    matches = result.get("matches", [])
    if not isinstance(matches, list):
        raise ExtractionError("Evidence context result has invalid matches")

    lines = ["## Evidence Context", "", f"**Query** {result.get('query', '')}", ""]
    if not matches:
        lines.append("_No grounded matches found._")
        return "\n".join(lines)

    for index, match in enumerate(matches, start=1):
        if not isinstance(match, dict):
            continue
        lines.extend(
            [
                f"### Match {index}",
                "",
                f"**Source Type** {match.get('source_type', '')}",
                f"**Locator** {match.get('locator', '')}",
                f"**Score** {match.get('score', '')}",
                "",
                str(match.get("snippet", "")).strip(),
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def save_evidence_context(workspace: Path, result: dict[str, object]) -> dict[str, str]:
    ensure_workspace(workspace)
    path = workspace / "evidence_context.md"
    append_text(path, format_evidence_context(result))
    return {"kind": "evidence_context", "path": str(path)}


def attach_evidence_context(
    workspace: Path,
    chapter: dict[str, object],
    query: str,
) -> dict[str, object]:
    if not query.strip():
        return {**chapter, "evidence_context": ""}
    context = build_evidence_context(workspace, query, str(chapter["id"]), 3)
    evidence_lines = [
        f"- {match['locator']}: {match['snippet']}"
        for match in context["matches"]
        if isinstance(match, dict)
    ]
    return {
        **chapter,
        "evidence_context": "\n".join(evidence_lines),
    }


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
    text = get_chapter_text(workspace, chapter_id)
    return {
        "id": chapter["id"],
        "title": chapter["title"],
        "line": chapter["line"],
        "text": text,
        "reading_guide": build_reading_guide(chapter["id"], chapter["title"], text),
    }


def check_feynman_summary(workspace: Path, chapter_id: str, summary: str) -> dict[str, object]:
    chapter = get_chapter(workspace, chapter_id)
    try:
        return build_provider().check_feynman_summary(
            attach_evidence_context(workspace, chapter, summary),
            summary,
        )
    except (RuntimeError, ValueError) as exc:
        raise ExtractionError(str(exc)) from exc


def explain_selection(
    workspace: Path,
    chapter_id: str,
    selected_text: str,
    language: str | None = None,
) -> dict[str, str]:
    chapter = get_chapter(workspace, chapter_id)
    try:
        return build_provider().explain_selection(
            attach_evidence_context(workspace, chapter, selected_text),
            selected_text,
            language,
        )
    except (RuntimeError, ValueError) as exc:
        raise ExtractionError(str(exc)) from exc


def generate_selection_review_question(
    workspace: Path,
    chapter_id: str,
    selected_text: str,
    language: str | None = None,
) -> dict[str, str]:
    chapter = get_chapter(workspace, chapter_id)
    try:
        return build_provider().generate_selection_review_question(
            attach_evidence_context(workspace, chapter, selected_text),
            selected_text,
            language,
        )
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
