"""Export reading workspace notes to an Obsidian folder."""

from __future__ import annotations

import shutil
from pathlib import Path

from .errors import ExtractionError
from .reader import load_metadata

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

ADVANCED_FILES = [
    "book_map.md",
    "concept_map.md",
    "argument_maps.md",
    "xray_notes.md",
    "napkin.md",
    "multi_source_map.md",
    "sources.md",
]

EXPORT_MODES = {"learning_archive", "full"}


def markdown_files(workspace: Path) -> list[Path]:
    return sorted(
        path
        for path in workspace.rglob("*.md")
        if path.is_file() and ".git" not in path.relative_to(workspace).parts
    )


def obsidian_link(path: Path) -> str:
    return f"[[{path.with_suffix('').as_posix()}]]"


def archive_file_name(chapter_id: str, title: str) -> str:
    safe_title = "".join(
        "-" if char in {"/", "\\", ":", "*", "?", '"', "<", ">", "|"} else char
        for char in title
    ).strip()
    return f"{chapter_id} {safe_title or chapter_id}.md"


def archive_chapter_path(chapter: dict[str, object]) -> Path:
    return Path("Chapter Notes") / archive_file_name(str(chapter["id"]), str(chapter["title"]))


def archive_chapter_link(chapter: dict[str, object]) -> str:
    return obsidian_link(archive_chapter_path(chapter))


def item_text(item: dict[str, object]) -> str:
    return str(item.get("content", "")).strip()


def item_bullet(item: dict[str, object]) -> str:
    locator = str(item.get("locator", "")).strip()
    content = item_text(item)
    if locator:
        return f"- **{locator}**\n\n  {content.replace(chr(10), chr(10) + '  ')}"
    return f"- {content.replace(chr(10), chr(10) + '  ')}"


def items_by_chapter(items: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in items:
        chapter_id = item.get("chapter_id")
        if not chapter_id:
            continue
        grouped.setdefault(str(chapter_id), []).append(item)
    return grouped


def items_of_kind(items: list[dict[str, object]], kind: str) -> list[dict[str, object]]:
    return [item for item in items if item.get("kind") == kind]


def chapter_by_id(status: dict[str, object]) -> dict[str, dict[str, object]]:
    learning_loop = status.get("learning_loop", {})
    if not isinstance(learning_loop, dict):
        return {}
    chapters = learning_loop.get("chapters", [])
    if not isinstance(chapters, list):
        return {}
    return {
        str(chapter.get("id")): chapter
        for chapter in chapters
        if isinstance(chapter, dict) and chapter.get("id")
    }


def next_action_text(status: dict[str, object]) -> str:
    continue_reading = status.get("continue_reading", {})
    if not isinstance(continue_reading, dict):
        return "继续阅读或复习当前材料。"
    next_action = continue_reading.get("next_action", {})
    if not isinstance(next_action, dict):
        return "继续阅读或复习当前材料。"
    kind = str(next_action.get("kind", ""))
    chapter_id = next_action.get("chapter_id")
    title = next_action.get("title")
    label = f"{chapter_id}: {title}" if chapter_id and title else ""
    if kind == "continue_current":
        return f"继续当前章节：{label}"
    if kind == "review_completed":
        return f"复习已读章节：{label}"
    if kind == "start_next":
        return f"开始下一章：{label}"
    if kind == "synthesize_book":
        return "进行全书综合。"
    return "继续阅读或复习当前材料。"


def chapter_link_from_id(chapter_id: str | None, chapters: list[dict[str, object]]) -> str:
    if not chapter_id:
        return ""
    for chapter in chapters:
        if str(chapter.get("id")) == chapter_id:
            return archive_chapter_link(chapter)
    return ""


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


def export_full_workspace(workspace: Path, vault_folder: Path) -> dict[str, object]:
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
        "mode": "full",
        "markdown_files_exported": len(exported),
        "index_path": str(index_path),
        "files": [str(path) for path in exported],
    }


def build_dashboard(
    workspace: Path,
    status: dict[str, object],
    journal: dict[str, object],
    chapters: list[dict[str, object]],
) -> str:
    metadata = load_metadata(workspace)
    title = str(metadata.get("title") or workspace.name)
    learning_loop = status.get("learning_loop", {})
    continue_reading = status.get("continue_reading", {})
    items = [item for item in journal.get("items", []) if isinstance(item, dict)]
    quotes = items_of_kind(items, "quote")[:5]
    questions = items_of_kind(items, "question")[:5]
    evidence = items_of_kind(items, "evidence_card")[:5]
    weak_chapters = (
        learning_loop.get("weak_chapters", []) if isinstance(learning_loop, dict) else []
    )
    weak_concepts = (
        learning_loop.get("weak_concepts", []) if isinstance(learning_loop, dict) else []
    )
    completed_count = (
        learning_loop.get("completed_count", 0) if isinstance(learning_loop, dict) else 0
    )
    average_mastery = (
        learning_loop.get("average_mastery", 0) if isinstance(learning_loop, dict) else 0
    )
    current_chapter = (
        continue_reading.get("current_chapter", {}) if isinstance(continue_reading, dict) else {}
    )
    current_id = str(current_chapter.get("id", "")) if isinstance(current_chapter, dict) else ""
    current_link = chapter_link_from_id(current_id, chapters)

    lines = [
        f"# {title}",
        "",
        "## 当前进度",
        "",
        f"- 当前章节：{current_link or '尚未开始'}",
        f"- 下一步：{next_action_text(status)}",
        f"- 总章节数：{len(chapters)}",
        f"- 已完成章节：{completed_count}",
        f"- 平均掌握度：{average_mastery}%",
        "",
        "## 快速入口",
        "",
        "- [[Review Queue]]",
        "- [[Evidence Cards]]",
        "",
    ]
    if chapters:
        lines.extend(["## 章节笔记", ""])
        lines.extend(f"- {archive_chapter_link(chapter)}" for chapter in chapters)
        lines.append("")
    lines.extend(["## 薄弱点", ""])
    if weak_chapters:
        for chapter in weak_chapters[:8]:
            if isinstance(chapter, dict):
                lines.append(
                    f"- {chapter_link_from_id(str(chapter.get('id', '')), chapters)} "
                    f"({chapter.get('mastery_score', 0)}%)"
                )
    else:
        lines.append("- 暂无薄弱章节。")
    if weak_concepts:
        lines.append("")
        lines.append("### 薄弱概念")
        lines.extend(
            f"- {item.get('concept', '')}: {item.get('note', '')}"
            for item in weak_concepts[:8]
            if isinstance(item, dict)
        )
    lines.extend(["", "## 最近摘录", ""])
    lines.extend(item_bullet(item) for item in quotes) if quotes else lines.append(
        "- 暂无摘录。"
    )
    lines.extend(["", "## 最近困惑", ""])
    lines.extend(item_bullet(item) for item in questions) if questions else lines.append(
        "- 暂无困惑。"
    )
    lines.extend(["", "## 最近证据", ""])
    lines.extend(item_bullet(item) for item in evidence) if evidence else lines.append(
        "- 暂无证据卡。"
    )
    lines.extend(["", "## 高级材料", "", "- [[Advanced]]"])
    return "\n".join(lines).rstrip() + "\n"


def build_review_queue(status: dict[str, object], journal: dict[str, object]) -> str:
    learning_loop = status.get("learning_loop", {})
    review_ready = learning_loop.get("review_ready", []) if isinstance(learning_loop, dict) else []
    weak_chapters = (
        learning_loop.get("weak_chapters", []) if isinstance(learning_loop, dict) else []
    )
    items = [item for item in journal.get("items", []) if isinstance(item, dict)]
    review_cards = items_of_kind(items, "review_card")
    lines = ["# Review Queue", "", "## 待复习章节", ""]
    if review_ready:
        lines.extend(
            f"- [ ] {chapter.get('id')}: {chapter.get('title')}：用 3-5 句话复述本章主张。"
            for chapter in review_ready
            if isinstance(chapter, dict)
        )
    else:
        lines.append("- 暂无待复习章节。")
    lines.extend(["", "## 薄弱章节复述", ""])
    if weak_chapters:
        lines.extend(
            f"- [ ] {chapter.get('id')}: {chapter.get('title')}：解释薄弱点并补一个证据。"
            for chapter in weak_chapters
            if isinstance(chapter, dict)
        )
    else:
        lines.append("- 暂无薄弱章节。")
    lines.extend(["", "## 复习卡", ""])
    lines.extend(f"- [ ] {item_text(item)}" for item in review_cards) if review_cards else (
        lines.append("- 暂无复习卡。")
    )
    return "\n".join(lines).rstrip() + "\n"


def build_evidence_archive(journal: dict[str, object], chapters: list[dict[str, object]]) -> str:
    items = [item for item in journal.get("items", []) if isinstance(item, dict)]
    evidence_items = items_of_kind(items, "evidence_card")
    lines = ["# Evidence Cards", ""]
    if not evidence_items:
        lines.append("暂无证据卡。")
        return "\n".join(lines).rstrip() + "\n"
    for item in evidence_items:
        chapter_link = chapter_link_from_id(
            str(item.get("chapter_id")) if item.get("chapter_id") else None,
            chapters,
        )
        lines.extend(
            [
                f"## {item.get('title', 'Evidence Card')}",
                "",
                f"- 来源：{item.get('locator', '')}",
                f"- 章节：{chapter_link or '未识别'}",
                "",
                item_text(item),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_chapter_archive(
    chapter: dict[str, object],
    chapter_status: dict[str, object],
    grouped_items: dict[str, list[dict[str, object]]],
) -> str:
    chapter_id = str(chapter["id"])
    items = grouped_items.get(chapter_id, [])
    notes = [item for item in items if item.get("kind") == "note"]
    quotes = [item for item in items if item.get("kind") == "quote"]
    questions = [item for item in items if item.get("kind") == "question"]
    reviews = [item for item in items if item.get("kind") == "review_card"]
    evidence = [item for item in items if item.get("kind") == "evidence_card"]
    lines = [
        f"# {chapter_id} {chapter['title']}",
        "",
        "## 本章状态",
        "",
        f"- 状态：{chapter_status.get('state', 'not-started')}",
        f"- 掌握度：{chapter_status.get('mastery_score', 0)}%",
        "",
        "## 本章我理解了什么",
        "",
    ]
    lines.extend(item_bullet(item) for item in notes) if notes else lines.append("- 暂无理解笔记。")
    lines.extend(["", "## 关键摘录", ""])
    lines.extend(item_bullet(item) for item in quotes) if quotes else lines.append(
        "- 暂无摘录。"
    )
    lines.extend(["", "## 我的困惑", ""])
    lines.extend(item_bullet(item) for item in questions) if questions else lines.append(
        "- 暂无困惑。"
    )
    lines.extend(["", "## AI 解释", ""])
    ai_notes = [item for item in notes if str(item.get("title", "")).lower().startswith("ai")]
    lines.extend(item_bullet(item) for item in ai_notes) if ai_notes else lines.append(
        "- 暂无 AI 解释。"
    )
    lines.extend(["", "## 复习问题", ""])
    lines.extend(item_bullet(item) for item in reviews) if reviews else lines.append(
        "- 暂无复习问题。"
    )
    lines.extend(["", "## 证据卡", ""])
    lines.extend(item_bullet(item) for item in evidence) if evidence else lines.append(
        "- 暂无证据卡。"
    )
    return "\n".join(lines).rstrip() + "\n"


def export_learning_archive(workspace: Path, vault_folder: Path) -> dict[str, object]:
    if not workspace.exists() or not workspace.is_dir():
        raise ExtractionError(f"Workspace not found: {workspace}")

    from .service import build_learning_journal, get_status

    status = get_status(workspace)
    journal = build_learning_journal(workspace)
    metadata = load_metadata(workspace)
    chapters = [
        chapter
        for chapter in metadata.get("chapters", [])
        if isinstance(chapter, dict) and chapter.get("id")
    ]
    chapter_statuses = chapter_by_id(status)
    items = [item for item in journal.get("items", []) if isinstance(item, dict)]
    grouped_items = items_by_chapter(items)

    vault_folder.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []

    files_to_write = {
        Path("Book Dashboard.md"): build_dashboard(workspace, status, journal, chapters),
        Path("Review Queue.md"): build_review_queue(status, journal),
        Path("Evidence Cards.md"): build_evidence_archive(journal, chapters),
    }
    for chapter in chapters:
        files_to_write[archive_chapter_path(chapter)] = build_chapter_archive(
            chapter,
            chapter_statuses.get(str(chapter["id"]), {}),
            grouped_items,
        )

    for relative, content in files_to_write.items():
        destination = vault_folder / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        exported.append(relative)

    advanced_dir = vault_folder / "Advanced"
    advanced_index = ["# Advanced", ""]
    for name in ADVANCED_FILES:
        source = workspace / name
        if not source.exists():
            continue
        destination = advanced_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        relative = Path("Advanced") / name
        exported.append(relative)
        advanced_index.append(f"- {obsidian_link(relative)}")
    if len(advanced_index) > 2:
        advanced_path = Path("Advanced.md")
        (vault_folder / advanced_path).write_text(
            "\n".join(advanced_index) + "\n",
            encoding="utf-8",
        )
        exported.append(advanced_path)

    index_path = vault_folder / "Book Dashboard.md"
    return {
        "vault_folder": str(vault_folder),
        "mode": "learning_archive",
        "markdown_files_exported": len(exported),
        "index_path": str(index_path),
        "files": [str(path) for path in exported],
    }


def export_obsidian_files(
    workspace: Path,
    vault_folder: Path,
    mode: str = "learning_archive",
) -> dict[str, object]:
    if mode not in EXPORT_MODES:
        raise ExtractionError(f"Unknown Obsidian export mode: {mode}")
    if mode == "full":
        return export_full_workspace(workspace, vault_folder)
    return export_learning_archive(workspace, vault_folder)


def export_obsidian(workspace: Path, vault_folder: Path, mode: str = "full") -> int:
    result = export_obsidian_files(workspace, vault_folder, mode)
    print(f"Obsidian export created: {vault_folder}")
    print(f"Markdown files exported: {result['markdown_files_exported']}")
    print(f"Index: {Path(str(result['index_path'])).name}")
    return 0


def cmd_export_obsidian(workspace: Path, vault_folder: Path) -> int:
    return export_obsidian(workspace, vault_folder)
