from pathlib import Path

import pytest
from deep_reading.cli import main
from deep_reading.errors import ExtractionError
from deep_reading.service import (
    add_evidence_card,
    add_insight,
    add_note,
    add_quote,
    add_review_card,
    export_obsidian,
    get_status,
    list_chapters,
    read_chapter,
    update_reading_state,
)


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


def test_list_chapters_returns_stateful_chapter_dicts(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    chapters = list_chapters(workspace)

    assert chapters[0] == {
        "id": "ch01",
        "title": "Intro",
        "line": chapters[0]["line"],
        "state": "not-started",
    }
    assert chapters[1] == {
        "id": "ch02",
        "title": "Practice",
        "line": chapters[1]["line"],
        "state": "not-started",
    }
    assert isinstance(chapters[0]["line"], int)
    assert isinstance(chapters[1]["line"], int)
    assert chapters[0]["line"] < chapters[1]["line"]


def test_get_status_returns_progress_and_artifacts(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    status = get_status(workspace)

    assert status["workspace"] == str(workspace)
    assert status["sources"] == 1
    assert status["current"] == "ch01"
    assert status["progress"] == {"not-started": 2}
    assert status["artifacts"]["evidence_cards.md"] is True


def test_read_chapter_returns_structured_text(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    chapter = read_chapter(workspace, "ch01")

    assert chapter["id"] == "ch01"
    assert chapter["title"] == "Intro"
    assert "Chapter 1 Intro" in str(chapter["text"])
    assert "Chapter 2 Practice" not in str(chapter["text"])


def test_update_reading_state_writes_state_file(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = update_reading_state(workspace, "ch02", "reading")

    assert result == {"chapter_id": "ch02", "state": "reading", "current": "ch02"}
    assert list_chapters(workspace)[1]["state"] == "reading"


def test_update_reading_state_rejects_invalid_state(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    with pytest.raises(ExtractionError, match="Invalid state"):
        update_reading_state(workspace, "ch01", "invalid")


def test_add_note_returns_written_path(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = add_note(workspace, "ch01", "Confusions", "What is the main distinction?")

    assert result["kind"] == "chapter_note"
    assert result["chapter_id"] == "ch01"
    assert Path(result["path"]).exists()
    assert "What is the main distinction?" in Path(result["path"]).read_text(encoding="utf-8")


def test_add_quote_appends_selected_text_to_chapter_note(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = add_quote(
        workspace,
        "ch01",
        "This selected sentence matters.",
        "ch01: Intro",
    )

    assert result["kind"] == "quote"
    assert result["chapter_id"] == "ch01"
    content = Path(result["path"]).read_text(encoding="utf-8")
    assert "## Quote" in content
    assert "**Locator** ch01: Intro" in content
    assert "> This selected sentence matters." in content


def test_add_insight_review_and_evidence_cards_return_paths(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    insight = add_insight(workspace, "This applies to my research workflow.")
    review = add_review_card(workspace, "What changed?", "The reading process became active.")
    evidence = add_evidence_card(
        workspace,
        claim="The chapter frames the core problem.",
        locator="ch01",
        support="The opening question defines the comparison.",
        confidence="High",
    )

    assert Path(insight["path"]).exists()
    assert Path(review["path"]).exists()
    assert Path(evidence["path"]).exists()
    assert "This applies to my research workflow." in Path(insight["path"]).read_text(
        encoding="utf-8"
    )
    assert "What changed?" in Path(review["path"]).read_text(encoding="utf-8")
    assert "The chapter frames the core problem." in Path(evidence["path"]).read_text(
        encoding="utf-8"
    )


def test_export_obsidian_returns_structured_result(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    vault_folder = tmp_path / "vault"

    result = export_obsidian(workspace, vault_folder)

    assert result["vault_folder"] == str(vault_folder)
    assert result["markdown_files_exported"] > 0
    assert Path(str(result["index_path"])).exists()
    assert "book_map.md" in result["files"]
