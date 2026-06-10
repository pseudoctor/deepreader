"""Export reading workspace notes to an Obsidian folder."""

from __future__ import annotations

import shutil
from pathlib import Path

from .errors import ExtractionError

CORE_FILES = [
    "reading-plan.md",
    "book_map.md",
    "questions.md",
    "concept_map.md",
    "review_cards.md",
    "personal_insights.md",
    "evidence_cards.md",
    "argument_maps.md",
    "xray_notes.md",
    "napkin.md",
    "multi_source_map.md",
    "sources.md",
]


def markdown_files(workspace: Path) -> list[Path]:
    return sorted(
        path
        for path in workspace.rglob("*.md")
        if path.is_file() and ".git" not in path.relative_to(workspace).parts
    )


def obsidian_link(path: Path) -> str:
    return f"[[{path.with_suffix('').as_posix()}]]"


def build_index(workspace: Path, exported_files: list[Path]) -> str:
    chapter_files = [
        path for path in exported_files if len(path.parts) > 1 and path.parts[0] == "chapter_notes"
    ]
    core_files = [Path(name) for name in CORE_FILES if Path(name) in exported_files]
    other_files = [
        path for path in exported_files if path not in core_files and path not in chapter_files
    ]

    lines = [
        "# Reading Index",
        "",
        f"Source workspace: `{workspace}`",
        "",
        "## Core Notes",
        "",
    ]
    lines.extend(f"- {obsidian_link(path)}" for path in core_files)

    lines.extend(["", "## Chapter Notes", ""])
    lines.extend(f"- {obsidian_link(path)}" for path in chapter_files)

    if other_files:
        lines.extend(["", "## Other Notes", ""])
        lines.extend(f"- {obsidian_link(path)}" for path in other_files)

    return "\n".join(lines).rstrip() + "\n"


def export_obsidian_files(workspace: Path, vault_folder: Path) -> dict[str, object]:
    if not workspace.exists() or not workspace.is_dir():
        raise ExtractionError(f"Workspace not found: {workspace}")

    files = markdown_files(workspace)
    if not files:
        raise ExtractionError(f"No Markdown files found in workspace: {workspace}")

    vault_folder.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    for source in files:
        relative = source.relative_to(workspace)
        destination = vault_folder / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        exported.append(relative)

    index_path = vault_folder / "index.md"
    index_path.write_text(build_index(workspace, exported), encoding="utf-8")
    return {
        "vault_folder": str(vault_folder),
        "markdown_files_exported": len(exported),
        "index_path": str(index_path),
        "files": [str(path) for path in exported],
    }


def export_obsidian(workspace: Path, vault_folder: Path) -> int:
    result = export_obsidian_files(workspace, vault_folder)
    print(f"Obsidian export created: {vault_folder}")
    print(f"Markdown files exported: {result['markdown_files_exported']}")
    print("Index: index.md")
    return 0


def cmd_export_obsidian(workspace: Path, vault_folder: Path) -> int:
    return export_obsidian(workspace, vault_folder)
