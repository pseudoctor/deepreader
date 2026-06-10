import json
from pathlib import Path

from deep_reading.cli import main
from deep_reading.errors import ExtractionError
from deep_reading.reader import get_chapter_text


def make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / "source_text").mkdir(parents=True)
    (workspace / "source_text" / "full_text.txt").write_text(
        "\n".join(
            [
                "CHAPTER1 First",
                "First body.",
                "",
                "More first body.",
                "CHAPTER2 Second",
                "Second body.",
                "CHAPTER3 Third",
                "Third body.",
                "Final line.",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "metadata.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {"id": "ch01", "title": "First", "line": 1},
                    {"id": "ch02", "title": "Second", "line": 5},
                    {"id": "ch03", "title": "Third", "line": 7},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return workspace


def test_get_chapter_text_reads_first_chapter_without_next_chapter(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    text = get_chapter_text(workspace, "ch01")

    assert "CHAPTER1 First" in text
    assert "More first body." in text
    assert "CHAPTER2 Second" not in text


def test_get_chapter_text_reads_middle_chapter(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    text = get_chapter_text(workspace, "ch02")

    assert text == "CHAPTER2 Second\nSecond body."


def test_get_chapter_text_reads_last_chapter_to_end(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    text = get_chapter_text(workspace, "ch03")

    assert text == "CHAPTER3 Third\nThird body.\nFinal line."


def test_get_chapter_text_rejects_unknown_chapter(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    try:
        get_chapter_text(workspace, "ch99")
    except ExtractionError as exc:
        assert "Unknown chapter: ch99" in str(exc)
    else:
        raise AssertionError("Expected ExtractionError")


def test_chapter_text_command_prints_chapter_text(tmp_path: Path, capsys) -> None:
    workspace = make_workspace(tmp_path)

    assert main(["chapter-text", str(workspace), "ch02"]) == 0

    output = capsys.readouterr().out
    assert "CHAPTER2 Second" in output
    assert "CHAPTER3 Third" not in output
