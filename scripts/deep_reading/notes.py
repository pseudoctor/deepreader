"""Commands for adding notes while reading."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .errors import ExtractionError


def ensure_workspace(workspace: Path) -> None:
    if not workspace.exists() or not workspace.is_dir():
        raise ExtractionError(f"Workspace not found: {workspace}")


def append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing.rstrip() + "\n\n" + content.rstrip() + "\n", encoding="utf-8")


def chapter_note_path(workspace: Path, chapter_id: str) -> Path:
    ensure_workspace(workspace)
    notes = sorted((workspace / "chapter_notes").glob(f"{chapter_id}-*.md"))
    if not notes:
        raise ExtractionError(f"No chapter note found for {chapter_id}")
    return notes[0]


def append_to_section(path: Path, section: str, content: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    heading = f"## {section}".casefold()
    insert_at: int | None = None

    for index, line in enumerate(lines):
        if line.strip().casefold() != heading:
            continue
        insert_at = len(lines)
        for next_index in range(index + 1, len(lines)):
            if lines[next_index].startswith("## "):
                insert_at = next_index
                break
        break

    if insert_at is None:
        raise ExtractionError(f"Section not found in {path.name}: {section}")

    block = ["", f"### Note {date.today().isoformat()}", "", content.rstrip(), ""]
    updated = lines[:insert_at] + block + lines[insert_at:]
    path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def cmd_note(workspace: Path, chapter_id: str, section: str, text: str) -> int:
    path = chapter_note_path(workspace, chapter_id)
    append_to_section(path, section, text)
    print(f"Note added: {path}")
    return 0


def cmd_insight(workspace: Path, text: str) -> int:
    ensure_workspace(workspace)
    path = workspace / "personal_insights.md"
    append_to_section(path, "Ideas To Apply", text)
    print(f"Insight added: {path}")
    return 0


def cmd_review_card(workspace: Path, question: str, answer: str) -> int:
    ensure_workspace(workspace)
    path = workspace / "review_cards.md"
    append_text(path, f"- Q: {question}\n  A: {answer}")
    print(f"Review card added: {path}")
    return 0


def cmd_evidence(
    workspace: Path,
    claim: str,
    locator: str,
    support: str,
    confidence: str,
    not_explicit: str,
    inference: str,
) -> int:
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
    print(f"Evidence card added: {path}")
    return 0
