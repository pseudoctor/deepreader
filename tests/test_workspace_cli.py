import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from deep_reading.cli import main
from deep_reading.errors import ExtractionError
from deep_reading.workspace import build_workspace


def make_sample_source(tmp_path: Path) -> Path:
    source = tmp_path / "sample.md"
    source.write_text(
        "# Chapter 1 Intro\n\n"
        "This is a short sample.\n\n"
        "# Chapter 2 Practice\n\n"
        "Another section for testing.\n",
        encoding="utf-8",
    )
    return source


def test_init_creates_workspace_artifacts(tmp_path: Path) -> None:
    source = make_sample_source(tmp_path)
    workspace = tmp_path / "workspace"

    assert main(["init", str(source), "--workspace", str(workspace)]) == 0

    metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    state = json.loads((workspace / "reading_state.json").read_text(encoding="utf-8"))

    assert metadata["total_sources"] == 1
    assert metadata["chapters_detected"] == 2
    assert metadata["note_language"] == "auto"
    assert state == {
        "current": "ch01",
        "chapters": {"ch01": "not-started", "ch02": "not-started"},
    }
    assert (workspace / "source_text" / "full_text.txt").exists()
    assert (workspace / "chapter_notes" / "ch01-intro.md").exists()


def test_init_does_not_overwrite_existing_workspace(tmp_path: Path) -> None:
    source = make_sample_source(tmp_path)
    workspace = tmp_path / "workspace"

    assert main(["init", str(source), "--workspace", str(workspace)]) == 0
    assert main(["mark", str(workspace), "ch01", "--state", "done"]) == 0
    plan = workspace / "reading-plan.md"
    plan.write_text("User-edited plan\n", encoding="utf-8")

    assert main(["init", str(source), "--workspace", str(workspace)]) == 1

    state = json.loads((workspace / "reading_state.json").read_text(encoding="utf-8"))
    assert state["chapters"]["ch01"] == "done"
    assert plan.read_text(encoding="utf-8") == "User-edited plan\n"


def test_init_does_not_overwrite_generated_file_in_existing_directory(tmp_path: Path) -> None:
    source = make_sample_source(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    book_map = workspace / "book_map.md"
    book_map.write_text("Existing notes\n", encoding="utf-8")

    with pytest.raises(ExtractionError, match="Workspace already exists"):
        build_workspace(str(source), workspace)

    assert book_map.read_text(encoding="utf-8") == "Existing notes\n"


def test_module_cli_init_creates_workspace_artifacts(tmp_path: Path) -> None:
    source = make_sample_source(tmp_path)
    workspace = tmp_path / "workspace"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "deep_reading.cli",
            "init",
            str(source),
            "--workspace",
            str(workspace),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "scripts"),
        },
    )

    assert result.returncode == 0
    assert (workspace / "metadata.json").exists()
    assert (workspace / "source_text" / "full_text.txt").exists()


def test_init_saves_user_selected_note_language(tmp_path: Path) -> None:
    source = make_sample_source(tmp_path)
    workspace = tmp_path / "workspace"

    assert (
        main(["init", str(source), "--workspace", str(workspace), "--note-language", "zh"])
        == 0
    )

    metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    library = json.loads((workspace / "library.json").read_text(encoding="utf-8"))
    chapter_note = (workspace / "chapter_notes" / "ch01-intro.md").read_text(encoding="utf-8")

    assert metadata["note_language"] == "zh"
    assert library["note_language"] == "zh"
    assert "> Note Language: zh" in chapter_note


def test_build_workspace_reports_source_extraction_details(tmp_path: Path) -> None:
    source = tmp_path / "book.azw3"
    source.write_text("unsupported", encoding="utf-8")

    with pytest.raises(ExtractionError, match="Unsupported file type: book.azw3"):
        build_workspace(str(source), tmp_path / "workspace")


def test_mark_updates_reading_state(tmp_path: Path) -> None:
    source = make_sample_source(tmp_path)
    workspace = tmp_path / "workspace"

    assert main(["init", str(source), "--workspace", str(workspace)]) == 0
    assert main(["mark", str(workspace), "ch02", "--state", "reading"]) == 0

    state = json.loads((workspace / "reading_state.json").read_text(encoding="utf-8"))
    assert state["current"] == "ch02"
    assert state["chapters"]["ch02"] == "reading"


def test_status_reports_invalid_reading_state(tmp_path: Path, capsys) -> None:
    source = make_sample_source(tmp_path)
    workspace = tmp_path / "workspace"
    assert main(["init", str(source), "--workspace", str(workspace)]) == 0
    (workspace / "reading_state.json").write_text("{not-json", encoding="utf-8")

    assert main(["status", str(workspace)]) == 1
    assert "Invalid reading_state.json" in capsys.readouterr().err


def test_status_reports_invalid_state_value_type(tmp_path: Path, capsys) -> None:
    source = make_sample_source(tmp_path)
    workspace = tmp_path / "workspace"
    assert main(["init", str(source), "--workspace", str(workspace)]) == 0
    (workspace / "reading_state.json").write_text(
        json.dumps({"current": "ch01", "chapters": {"ch01": []}}),
        encoding="utf-8",
    )

    assert main(["status", str(workspace)]) == 1
    assert "Invalid reading_state.json" in capsys.readouterr().err


def test_template_command_prints_known_template(tmp_path: Path, capsys) -> None:
    assert main(["template", str(tmp_path), "evidence"]) == 0

    output = capsys.readouterr().out
    assert "# Evidence Cards" in output
    assert "**Source Locator**" in output
