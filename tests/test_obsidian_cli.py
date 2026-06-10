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


def test_export_obsidian_copies_markdown_files_and_creates_index(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    vault_folder = tmp_path / "vault" / "Reading" / "sample"

    assert (
        main(
            [
                "export-obsidian",
                str(workspace),
                "--vault-folder",
                str(vault_folder),
            ]
        )
        == 0
    )

    assert (vault_folder / "book_map.md").exists()
    assert (vault_folder / "review_cards.md").exists()
    assert (vault_folder / "chapter_notes" / "ch01-intro.md").exists()

    index = (vault_folder / "index.md").read_text(encoding="utf-8")
    assert "# Reading Index" in index
    assert "[[book_map]]" in index
    assert "[[chapter_notes/ch01-intro]]" in index


def test_export_obsidian_overwrites_existing_markdown_file(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    vault_folder = tmp_path / "vault"
    vault_folder.mkdir()
    (vault_folder / "book_map.md").write_text("stale", encoding="utf-8")

    assert (
        main(
            [
                "export-obsidian",
                str(workspace),
                "--vault-folder",
                str(vault_folder),
            ]
        )
        == 0
    )

    assert "stale" not in (vault_folder / "book_map.md").read_text(encoding="utf-8")


def test_export_obsidian_returns_error_for_missing_workspace(tmp_path: Path) -> None:
    result = main(
        [
            "export-obsidian",
            str(tmp_path / "missing"),
            "--vault-folder",
            str(tmp_path / "vault"),
        ]
    )

    assert result == 1
