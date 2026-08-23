# Deepreader Product Development Plan

## Product Positioning

Deepreader should become a local-first AI deep reading coach for serious readers.

It is not a generic summarizer, read-it-later app, or document chatbot. Its core promise is:

> Help users read chapter by chapter, think before accepting summaries, record evidence, test understanding, and preserve the process as Obsidian-ready Markdown.

## Recommended Final Form

The best final form is a desktop app.

Recommended stack:

- React
- Electron
- TypeScript
- Python `deep_reading` engine
- Local Markdown workspace
- Optional OpenAI API or replaceable LLM provider
- Obsidian export and sync

Recommended development path:

```text
CLI foundation
  -> local Web MVP
  -> Electron desktop app
  -> AI Coach
  -> Obsidian and knowledge-base integration
```

## Stage 0: Product Validation And Technical Foundation

Estimated duration: 1 week.

Goal: prove the existing Python engine can serve as the app backend.

### Scope

- Stabilize the workspace data model.
- Add a chapter text API, such as `get_chapter_text(workspace, chapter_id)`.
- Expose workspace operations through functions that can later be called by a web or desktop layer.
- Define internal product entities:
  - Book
  - Chapter
  - Note
  - EvidenceCard
  - ReviewCard
  - ReadingState

### Technical Direction

- Keep the existing Python `deep_reading` modules.
- Add a local API layer only after the core reader functions are stable.
- Use pytest for chapter slicing and note-writing behavior.

### Acceptance Criteria

- A caller can read the chapter list from a workspace.
- A caller can read one chapter's text by chapter ID.
- A caller can read and update reading state.
- A caller can write notes, evidence cards, and review cards.
- `make check` passes.

## Stage 1: Local Web MVP

Estimated duration: 2-3 weeks.

Goal: make the core loop usable: read, think, write, save.

### Core Screens

- Library: open or select an existing workspace.
- Reader: chapter list on the left, chapter text in the center.
- Notes: structured note panel on the right.
- Cards: evidence cards and review cards.
- Export: export notes to Obsidian.

### Core Features

- Open an existing reading workspace.
- Show chapter list and progress state.
- Click a chapter to display its text.
- Mark chapter state:
  - not-started
  - reading
  - done
  - review
- Add structured chapter notes:
  - Confusions
  - Key Concepts
  - My Summary
  - Applications
- Add review cards.
- Add evidence cards.
- Export Markdown notes to an Obsidian folder.

### Technical Direction

- Backend: FastAPI plus existing Python modules.
- Frontend: React, TypeScript, Vite.
- UI: Tailwind CSS or shadcn/ui.
- Storage: local Markdown and JSON files.
- No database in the first version.

### Acceptance Criteria

- A user can complete one chapter reading session entirely in the UI.
- Notes are written back to the workspace Markdown files.
- Review cards and evidence cards are persisted.
- Obsidian export works from the UI.
- Backend tests and UI smoke tests pass.

## Stage 2: Electron Desktop App

Estimated duration: 2-3 weeks.

Goal: turn the local web experience into a real desktop reading app.

### Core Features

- Open EPUB, PDF, DOCX, Markdown, or existing workspace from a file picker.
- Choose workspace directory.
- Choose Obsidian Vault or target export folder.
- Remember recent workspaces.
- Start and manage the local Python backend from the app.
- Package a macOS build first.

### Technical Direction

Architecture:

```text
React Renderer
  -> preload.ts
  -> Electron IPC
  -> Python local backend
  -> workspace Markdown files
```

Responsibilities:

- Electron main process:
  - window management
  - file picker
  - local path permissions
  - backend process management
  - API key storage boundary
- React renderer:
  - reading UI
  - note editor
  - cards
  - progress controls
- Python backend:
  - source extraction
  - workspace management
  - notes
  - Obsidian export

### Acceptance Criteria

- The app starts without command-line usage.
- A user can open a book or workspace through the UI.
- A user can read a chapter and save notes.
- A user can export to Obsidian from the app.
- The macOS build can be installed and launched locally.

## Stage 3: AI Coach

Estimated duration: 3-4 weeks.

Goal: evolve from a reading tool into an active deep reading coach.

### AI Actions

Avoid a generic chatbot as the first interface. Start with explicit actions:

- Generate read-for questions.
- Check my summary with a Feynman-style diagnosis.
- Explain selected text.
- Generate an evidence card.
- Generate a review card.
- Generate a Toulmin argument map.
- Generate chapter concept links.
- Suggest the next reading step.

### Suggested Request Shape

```json
{
  "workspace": "...",
  "chapter_id": "ch01",
  "selected_text": "...",
  "user_note": "...",
  "mode": "feynman_check"
}
```

### Technical Direction

- Store API keys outside the renderer.
- Prefer environment variables or desktop secure storage.
- Do not expose API keys to React.
- Keep provider access behind a backend interface.
- Start with OpenAI API.
- Design a provider boundary so Anthropic, local models, or other APIs can be added later.
- Return structured data where possible, then write the result to Markdown.

### Acceptance Criteria

- The user can submit a 3-5 sentence chapter summary.
- AI returns a Feynman check:
  - accurate points
  - vague points
  - missing causal links
  - unsupported leaps
  - corrected version
- The user can save AI feedback into the chapter note.
- AI-generated review cards and evidence cards can be saved to workspace files.

## Stage 4: Obsidian Deep Integration

Estimated duration: 2 weeks.

Goal: make the app a strong companion for Obsidian users.

### Core Features

- Bind an Obsidian Vault folder.
- Export or sync the current book workspace.
- Generate `index.md`.
- Generate wiki links.
- Preserve `chapter_notes/` and card files.
- Add optional frontmatter.

### Suggested Frontmatter

```yaml
---
type: chapter-note
book:
chapter:
status:
tags:
  - reading
  - deep-reading
---
```

### Advanced Features

- Configurable note templates.
- Per-book Obsidian folder naming.
- Chapter backlinks.
- Export review cards.
- Export evidence cards.

### Acceptance Criteria

- Obsidian can browse the exported book index.
- Chapter notes link correctly.
- Evidence cards and review cards are accessible from the index.
- Re-exporting updates files predictably.

## Stage 5: Learning Loop

Estimated duration: 3-4 weeks.

Goal: help users retain and apply what they read.

### Core Features

- Chapter mastery score.
- Active recall mode.
- Weak concept tracking.
- Every-three-chapter synthesis.
- Whole-book X-Ray mode.
- Final outputs:
  - one-page book account
  - core argument chain
  - concept map
  - evidence table
  - action/application list

### Acceptance Criteria

- The app can show which chapters are read, reviewed, or weak.
- The user can run active recall for completed chapters.
- The app can synthesize across several chapters.
- Whole-book outputs remain grounded in chapter notes and evidence cards.

## Technical Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Zustand or Jotai

### Desktop

- Electron
- electron-builder
- preload plus IPC bridge

### Backend

- Python 3.11+
- FastAPI
- Pydantic
- Existing `deep_reading` modules

### AI

- OpenAI API first
- Provider interface for future model options
- API key stored outside frontend renderer

### Storage

- Markdown
- JSON metadata
- Local filesystem
- No SQLite in the first version

### Testing

- pytest
- ruff
- React Testing Library
- Playwright for end-to-end UI verification

## First Sellable Version

The smallest sellable version should include:

1. Open EPUB, PDF, DOCX, Markdown, or existing workspace.
2. Generate a reading workspace.
3. Read chapter by chapter.
4. Write structured notes while reading.
5. Generate read-for questions with AI.
6. Check the user's summary with AI.
7. Generate review cards.
8. Export to Obsidian.

## Intentional Non-Goals For Early Versions

Do not build these in the first version:

- Cloud sync
- User accounts
- Multi-user collaboration
- Mobile app
- Online bookstore
- Public community sharing
- Complex PDF coordinate-based highlight system
- Unlimited whole-book AI summarization

These features increase complexity before the core product loop is proven.

## Product Principle

The product should not replace reading.

It should make the user think, recall, explain, question, and preserve the evidence trail.

Short positioning:

> Not a summarizer. A coach that helps you actually understand the book.
