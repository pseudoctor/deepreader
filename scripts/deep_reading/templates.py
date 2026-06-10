"""Markdown and JSON templates for reading workspaces."""

from __future__ import annotations

from datetime import date
from pathlib import Path


def language_line(note_language: str) -> str:
    return f"> Note Language: {note_language}"


def reading_plan_template(
    title: str, chapters: list[dict[str, object]], note_language: str = "auto"
) -> str:
    chapter_list = "\n".join(f"- [ ] {c['id']}: {c['title']}" for c in chapters)
    return f"""# Reading Plan: {title}

{language_line(note_language)}

## Goal

Write the user's reading goal here.

## Route

{chapter_list}

## Checkpoints

- After each chapter: explain the core claim in 3-5 sentences.
- For important claims: add an evidence card with a locator.
- For argument-heavy chapters: create a Toulmin argument map.
- Every 3 chapters: synthesize connections and update `concept_map.md`.
- After each major part: run x-ray deep reading.
- End of book: write a one-page account of the book's argument and how to apply it.
- End of book: create `napkin.md` with one formula, one sentence, one ASCII diagram,
  and one action trigger.
"""


def book_map_template(
    title: str,
    chapters: list[dict[str, object]],
    sources: list[dict[str, object]],
    note_language: str = "auto",
) -> str:
    source_rows = "\n".join(
        f"- `{s['filename']}` via {s['method']} ({s['words']} words)" for s in sources
    )
    chapter_rows = "\n".join(f"| {c['id']} | {c['title']} | line {c['line']} | |" for c in chapters)
    return f"""# Book Map: {title}

{language_line(note_language)}

## Sources

{source_rows}

## Chapter Index

| ID | Title | Start | Notes |
|---|---|---:|---|
{chapter_rows}

## Core Questions

- What problem is this book trying to solve?
- What concepts does the author need the reader to learn?
- What would count as misunderstanding this book?
- Which claims need evidence cards?
- Which chapters need argument maps?
"""


def chapter_note_template(chapter_id: str, title: str, note_language: str = "auto") -> str:
    return f"""# {chapter_id}: {title}

{language_line(note_language)}

## Before Reading

- What do I expect this chapter to answer?
- What prior concept might this build on?

## Core Claim

TBD

## Evidence Cards

- Claim:
  Locator:
  Support:
  Confidence:
  Not explicit:

## Argument Path

1. TBD
2. TBD
3. TBD

## Toulmin Argument Map

- Claim:
- Grounds:
- Warrant:
- Backing:
- Qualifier:
- Rebuttal:
- Weak links:

## Key Concepts

- TBD

## Hidden Assumptions and Boundaries

- Assumption:
- Boundary:

## Confusions

- TBD

## My 3-5 Sentence Summary

TBD

## Coach Feedback

TBD

## Applications

- TBD
"""


def questions_template(note_language: str = "auto") -> str:
    return f"""# Questions

{language_line(note_language)}

## Active Recall

- Q:
  A:

## Socratic Questions

- Q:
  My answer:
  Coach feedback:

## Open Questions

- TBD
"""


def concept_map_template(note_language: str = "auto") -> str:
    return f"""# Concept Map

{language_line(note_language)}

```text
Central problem
  -> concept
     -> supports claim
     -> fails when
```
"""


def review_cards_template(note_language: str = "auto") -> str:
    return f"""# Review Cards

{language_line(note_language)}

- Q:
  A:
"""


def personal_insights_template(note_language: str = "auto") -> str:
    return f"""# Personal Insights

{language_line(note_language)}

## Ideas To Apply

- TBD

## Changed My Mind

- TBD

## Follow-Up Reading

- TBD
"""


def evidence_cards_template(note_language: str = "auto") -> str:
    return f"""# Evidence Cards

{language_line(note_language)}

Use this file for source-bound claims.

## Template

**Claim**

**Source Locator**
- Source:
- Chapter/Section:
- Page/Line/Heading:

**Support**

**Confidence**
High / Medium / Low

**Not Explicit / Needs Verification**

**My Inference**
"""


def argument_maps_template(note_language: str = "auto") -> str:
    return f"""# Argument Maps

{language_line(note_language)}

Use Toulmin-style maps for argument-heavy chapters.

## Template

**Claim**

**Grounds**

**Warrant**

**Backing**

**Qualifier**

**Rebuttal**

**Weak Links**
"""


def xray_notes_template(note_language: str = "auto") -> str:
    return f"""# X-Ray Notes

{language_line(note_language)}

## Round 1: Skeleton Scan

- Core question:
- Core answer:
- Chapter skeleton:
- Argument type:

## Round 2: Deep Dissection

- Reasoning chain:
- Strongest evidence:
- Hidden assumptions:
- Counterexamples:
- Boundaries:

## Round 3: Soul Extraction

- Worldview:
- Blind spots:
- Transferable patterns:
- Knowledge connections:
- Action triggers:
"""


def napkin_template(note_language: str = "auto") -> str:
    return f"""# Napkin

{language_line(note_language)}

## Formula

```text
A + B -> C
```

## One Sentence

TBD

## ASCII Diagram

```text
+----------------+
|                |
+----------------+
```

## Action Trigger

When TBD, I should TBD.
"""


def multi_source_map_template(
    sources: list[dict[str, object]], note_language: str = "auto"
) -> str:
    rows = "\n".join(
        f"| {s['filename']} | document | extracted via {s['method']} | not-read |" for s in sources
    )
    return f"""# Multi-Source Map

{language_line(note_language)}

## Material Level

Full text extracted. Confirm quality before making strong cross-source claims.

## Source Table

| Source | Type | Coverage | Status |
|---|---|---|---|
{rows}

## Core Concepts

- TBD

## Agreement Matrix

| Point | Sources | Evidence |
|---|---|---|

## Conflict Matrix

| Conflict | Source A | Source B | Why It Differs |
|---|---|---|---|

## Concept Lineage

```text
source A -> source B -> source C
```

## Evidence Gaps

- TBD
"""


def sources_template(sources: list[dict[str, object]], errors: list[dict[str, str]]) -> str:
    rows = "\n".join(
        (
            f"- `{s['filename']}`\n"
            f"  - method: {s['method']}\n"
            f"  - words: {s['words']}\n"
            f"  - path: {s['source_file']}"
        )
        for s in sources
    )
    error_rows = "\n".join(f"- `{e['file']}`: {e['error']}" for e in errors) or "- None"
    return f"""# Sources

## Processed Sources

{rows}

## Skipped Sources

{error_rows}

## Citation Notes

- Title:
- Author:
- Year:
- Publisher / Venue:
- DOI / ISBN:
- Citation status:
"""


def library_template(
    source: str,
    workspace: Path,
    sources: list[dict[str, object]],
    note_language: str = "auto",
) -> dict[str, object]:
    return {
        "workspace": str(workspace),
        "source_argument": source,
        "created": date.today().isoformat(),
        "note_language": note_language,
        "tags": [],
        "reading_goal": "",
        "sources": [
            {
                "filename": s["filename"],
                "path": s["source_file"],
                "method": s["method"],
                "words": s["words"],
                "status": "not-read",
                "topics": [],
                "important_chapters": [],
            }
            for s in sources
        ],
    }


TEMPLATE_BUILDERS = {
    "evidence": evidence_cards_template,
    "argument": argument_maps_template,
    "xray": xray_notes_template,
    "napkin": napkin_template,
    "review": review_cards_template,
    "concept": concept_map_template,
}
