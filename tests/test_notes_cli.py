import json
from pathlib import Path

from deep_reading.cli import main


def make_workspace(tmp_path: Path) -> Path:
    source = tmp_path / "sample.md"
    workspace = tmp_path / "workspace"
    source.write_text(
        "# Chapter 1 Intro\n\n"
        "This is a short sample.\n\n"
        "# Chapter 2 Practice\n\n"
        "Another section for testing.\n",
        encoding="utf-8",
    )
    assert main(["init", str(source), "--workspace", str(workspace)]) == 0
    return workspace


def test_note_appends_to_named_chapter_section(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    assert (
        main(
            [
                "note",
                str(workspace),
                "ch01",
                "--section",
                "Confusions",
                "--text",
                "I do not understand the core distinction yet.",
            ]
        )
        == 0
    )

    note = (workspace / "chapter_notes" / "ch01-intro.md").read_text(encoding="utf-8")
    assert "## Confusions" in note
    assert "### Note" in note
    assert "I do not understand the core distinction yet." in note


def test_note_returns_error_for_unknown_section(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = main(
        [
            "note",
            str(workspace),
            "ch01",
            "--section",
            "Missing Section",
            "--text",
            "This should fail.",
        ]
    )

    assert result == 1


def test_insight_appends_to_personal_insights(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    assert main(["insight", str(workspace), "--text", "Apply this idea to research notes."]) == 0

    content = (workspace / "personal_insights.md").read_text(encoding="utf-8")
    assert "## Ideas To Apply" in content
    assert "Apply this idea to research notes." in content


def test_review_card_appends_question_and_answer(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    assert (
        main(
            [
                "review-card",
                str(workspace),
                "--question",
                "What is the main claim?",
                "--answer",
                "The chapter makes a testable claim.",
            ]
        )
        == 0
    )

    content = (workspace / "review_cards.md").read_text(encoding="utf-8")
    assert "- Q: What is the main claim?" in content
    assert "  A: The chapter makes a testable claim." in content


def test_evidence_appends_structured_card(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    assert (
        main(
            [
                "evidence",
                str(workspace),
                "--claim",
                "The author introduces the main problem.",
                "--locator",
                "sample.md ch01",
                "--support",
                "The opening paragraph frames the problem.",
                "--confidence",
                "Medium",
                "--not-explicit",
                "The scope is still unclear.",
                "--inference",
                "This likely sets up chapter two.",
            ]
        )
        == 0
    )

    content = (workspace / "evidence_cards.md").read_text(encoding="utf-8")
    assert "## Evidence Card" in content
    assert "**Claim** The author introduces the main problem." in content
    assert "- sample.md ch01" in content
    assert "**Confidence** Medium" in content


def test_note_does_not_change_reading_state(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    before = json.loads((workspace / "reading_state.json").read_text(encoding="utf-8"))

    assert (
        main(
            [
                "note",
                str(workspace),
                "ch01",
                "--section",
                "Applications",
                "--text",
                "Use this during project reading.",
            ]
        )
        == 0
    )

    after = json.loads((workspace / "reading_state.json").read_text(encoding="utf-8"))
    assert after == before
