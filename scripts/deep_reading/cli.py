"""Command-line interface for reading workspace management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import ExtractionError
from .notes import cmd_evidence, cmd_insight, cmd_note, cmd_review_card
from .obsidian import cmd_export_obsidian
from .reader import cmd_chapter_text
from .state import (
    cmd_chapter,
    cmd_library,
    cmd_list,
    cmd_mark,
    cmd_source,
    cmd_status,
    cmd_template,
)
from .workspace import build_workspace, default_workspace_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create and maintain a deep-reading workspace.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init")
    init_p.add_argument("source")
    init_p.add_argument("--workspace", type=Path)
    init_p.add_argument(
        "--note-language",
        default="auto",
        help="Preferred language for generated notes, for example auto, zh, en, or ja.",
    )

    for name in ("status", "list", "source", "library"):
        p = sub.add_parser(name)
        p.add_argument("workspace", type=Path)

    chapter_p = sub.add_parser("chapter")
    chapter_p.add_argument("workspace", type=Path)
    chapter_p.add_argument("chapter_id")

    chapter_text_p = sub.add_parser("chapter-text")
    chapter_text_p.add_argument("workspace", type=Path)
    chapter_text_p.add_argument("chapter_id")

    mark_p = sub.add_parser("mark")
    mark_p.add_argument("workspace", type=Path)
    mark_p.add_argument("chapter_id")
    mark_p.add_argument("--state", required=True)

    template_p = sub.add_parser("template")
    template_p.add_argument("workspace", type=Path)
    template_p.add_argument("template_name")

    note_p = sub.add_parser("note")
    note_p.add_argument("workspace", type=Path)
    note_p.add_argument("chapter_id")
    note_p.add_argument("--section", required=True)
    note_p.add_argument("--text", required=True)

    insight_p = sub.add_parser("insight")
    insight_p.add_argument("workspace", type=Path)
    insight_p.add_argument("--text", required=True)

    review_card_p = sub.add_parser("review-card")
    review_card_p.add_argument("workspace", type=Path)
    review_card_p.add_argument("--question", required=True)
    review_card_p.add_argument("--answer", required=True)

    evidence_p = sub.add_parser("evidence")
    evidence_p.add_argument("workspace", type=Path)
    evidence_p.add_argument("--claim", required=True)
    evidence_p.add_argument("--locator", required=True)
    evidence_p.add_argument("--support", required=True)
    evidence_p.add_argument("--confidence", choices=["High", "Medium", "Low"], required=True)
    evidence_p.add_argument("--not-explicit", default="TBD")
    evidence_p.add_argument("--inference", default="TBD")

    obsidian_p = sub.add_parser("export-obsidian")
    obsidian_p.add_argument("workspace", type=Path)
    obsidian_p.add_argument("--vault-folder", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            workspace = args.workspace or default_workspace_for(args.source)
            return build_workspace(args.source, workspace, note_language=args.note_language)
        if args.command == "status":
            return cmd_status(args.workspace)
        if args.command == "list":
            return cmd_list(args.workspace)
        if args.command == "chapter":
            return cmd_chapter(args.workspace, args.chapter_id)
        if args.command == "chapter-text":
            return cmd_chapter_text(args.workspace, args.chapter_id)
        if args.command == "mark":
            return cmd_mark(args.workspace, args.chapter_id, args.state)
        if args.command == "source":
            return cmd_source(args.workspace)
        if args.command == "library":
            return cmd_library(args.workspace)
        if args.command == "template":
            return cmd_template(args.workspace, args.template_name)
        if args.command == "note":
            return cmd_note(args.workspace, args.chapter_id, args.section, args.text)
        if args.command == "insight":
            return cmd_insight(args.workspace, args.text)
        if args.command == "review-card":
            return cmd_review_card(args.workspace, args.question, args.answer)
        if args.command == "evidence":
            return cmd_evidence(
                args.workspace,
                args.claim,
                args.locator,
                args.support,
                args.confidence,
                args.not_explicit,
                args.inference,
            )
        if args.command == "export-obsidian":
            return cmd_export_obsidian(args.workspace, args.vault_folder)
    except ExtractionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
