"""Workspace status and state commands."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import ExtractionError
from .templates import TEMPLATE_BUILDERS
from .workspace import write


def load_state(workspace: Path) -> dict:
    state_path = workspace / "reading_state.json"
    if not state_path.exists():
        raise ExtractionError(f"Missing reading_state.json in {workspace}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def cmd_status(workspace: Path) -> int:
    metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    state = load_state(workspace)
    counts: dict[str, int] = {}
    for value in state["chapters"].values():
        counts[value] = counts.get(value, 0) + 1
    print(f"Workspace: {workspace}")
    print(f"Sources: {metadata['total_sources']}")
    print(f"Words: {metadata['words']:,}")
    print(f"Estimated tokens: ~{metadata['estimated_tokens'] // 1000}K")
    print(f"Current: {state.get('current')}")
    print("Progress:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    artifacts = [
        "evidence_cards.md",
        "argument_maps.md",
        "xray_notes.md",
        "napkin.md",
        "multi_source_map.md",
        "sources.md",
        "library.json",
    ]
    print("Artifacts:")
    for artifact in artifacts:
        print(f"  {'yes' if (workspace / artifact).exists() else 'no '} {artifact}")
    return 0


def cmd_list(workspace: Path) -> int:
    metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    state = load_state(workspace)
    for chapter in metadata["chapters"]:
        chapter_state = state["chapters"].get(chapter["id"], "not-started")
        print(f"{chapter['id']}\t{chapter_state}\t{chapter['title']}")
    return 0


def cmd_chapter(workspace: Path, chapter_id: str) -> int:
    notes = sorted((workspace / "chapter_notes").glob(f"{chapter_id}-*.md"))
    if not notes:
        raise ExtractionError(f"No chapter note found for {chapter_id}")
    print(notes[0])
    print(notes[0].read_text(encoding="utf-8"))
    return 0


def cmd_mark(workspace: Path, chapter_id: str, state_value: str) -> int:
    allowed = {"not-started", "reading", "done", "review"}
    if state_value not in allowed:
        raise ExtractionError(
            f"Invalid state '{state_value}'. Use one of: {', '.join(sorted(allowed))}"
        )
    state = load_state(workspace)
    if chapter_id not in state["chapters"]:
        raise ExtractionError(f"Unknown chapter: {chapter_id}")
    state["chapters"][chapter_id] = state_value
    state["current"] = chapter_id
    write(workspace / "reading_state.json", json.dumps(state, indent=2))
    print(f"{chapter_id} -> {state_value}")
    return 0


def cmd_source(workspace: Path) -> int:
    path = workspace / "sources.md"
    if not path.exists():
        raise ExtractionError(f"Missing sources.md in {workspace}")
    print(path.read_text(encoding="utf-8"))
    return 0


def cmd_library(workspace: Path) -> int:
    path = workspace / "library.json"
    if not path.exists():
        raise ExtractionError(f"Missing library.json in {workspace}")
    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_template(workspace: Path, template_name: str) -> int:
    if template_name not in TEMPLATE_BUILDERS:
        options = ", ".join(sorted(TEMPLATE_BUILDERS))
        raise ExtractionError(
            f"Unknown template '{template_name}'. Use one of: {options}"
        )
    print(TEMPLATE_BUILDERS[template_name]())
    return 0
