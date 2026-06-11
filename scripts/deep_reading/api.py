"""FastAPI app exposing read-only workspace operations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .errors import ExtractionError
from .service import (
    add_evidence_card,
    add_note,
    add_quote,
    add_review_card,
    build_book_argument_map,
    check_feynman_summary,
    explain_selection,
    export_obsidian,
    generate_selection_review_question,
    get_status,
    list_chapters,
    read_chapter,
    save_book_argument_map,
    synthesize_chapter_window,
    update_reading_state,
)

WorkspaceQuery = Annotated[Path, Query()]
ChapterIdQuery = Annotated[str, Query()]


app = FastAPI(title="Deep Reading API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "null"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class StateRequest(BaseModel):
    workspace: Path
    chapter_id: str
    state: str


class NoteRequest(BaseModel):
    workspace: Path
    chapter_id: str
    section: str
    text: str
    note_type: str = Field(
        default="My Thought",
        pattern="^(Quote|My Thought|AI Explanation|Question)$",
    )


class QuoteRequest(BaseModel):
    workspace: Path
    chapter_id: str
    quote: str
    locator: str


class FeynmanCheckRequest(BaseModel):
    workspace: Path
    chapter_id: str
    summary: str


class SelectionActionRequest(BaseModel):
    workspace: Path
    chapter_id: str
    selected_text: str


class ChapterSynthesisRequest(BaseModel):
    workspace: Path
    start_chapter_id: str
    count: int = Field(default=3, ge=1, le=10)


class BookArgumentMapRequest(BaseModel):
    workspace: Path


class SaveBookArgumentMapRequest(BaseModel):
    workspace: Path
    result: dict[str, object]


class ReviewCardRequest(BaseModel):
    workspace: Path
    question: str
    answer: str


class EvidenceCardRequest(BaseModel):
    workspace: Path
    claim: str
    locator: str
    support: str
    confidence: str = Field(pattern="^(High|Medium|Low)$")
    not_explicit: str = "TBD"
    inference: str = "TBD"


class ObsidianExportRequest(BaseModel):
    workspace: Path
    vault_folder: Path


@app.exception_handler(ExtractionError)
async def extraction_error_handler(request, exc: ExtractionError) -> JSONResponse:  # noqa: ANN001
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status(workspace: WorkspaceQuery) -> dict[str, object]:
    return get_status(workspace)


@app.get("/chapters")
def chapters(workspace: WorkspaceQuery) -> dict[str, object]:
    return {"chapters": list_chapters(workspace)}


@app.get("/chapter-text")
def chapter_text(
    workspace: WorkspaceQuery,
    chapter_id: ChapterIdQuery,
) -> dict[str, object]:
    return read_chapter(workspace, chapter_id)


@app.post("/state")
def state(request: StateRequest) -> dict[str, str]:
    return update_reading_state(request.workspace, request.chapter_id, request.state)


@app.post("/notes")
def notes(request: NoteRequest) -> dict[str, str]:
    return add_note(
        request.workspace,
        request.chapter_id,
        request.section,
        request.text,
        request.note_type,
    )


@app.post("/quotes")
def quotes(request: QuoteRequest) -> dict[str, str]:
    return add_quote(request.workspace, request.chapter_id, request.quote, request.locator)


@app.post("/feynman-check")
def feynman_check(request: FeynmanCheckRequest) -> dict[str, object]:
    return check_feynman_summary(request.workspace, request.chapter_id, request.summary)


@app.post("/selection-explanation")
def selection_explanation(request: SelectionActionRequest) -> dict[str, str]:
    return explain_selection(request.workspace, request.chapter_id, request.selected_text)


@app.post("/selection-review-question")
def selection_review_question(request: SelectionActionRequest) -> dict[str, str]:
    return generate_selection_review_question(
        request.workspace,
        request.chapter_id,
        request.selected_text,
    )


@app.post("/chapter-synthesis")
def chapter_synthesis(request: ChapterSynthesisRequest) -> dict[str, object]:
    return synthesize_chapter_window(
        request.workspace,
        request.start_chapter_id,
        request.count,
    )


@app.post("/book-argument-map")
def book_argument_map(request: BookArgumentMapRequest) -> dict[str, object]:
    return build_book_argument_map(request.workspace)


@app.post("/book-argument-map/save")
def save_argument_map(request: SaveBookArgumentMapRequest) -> dict[str, str]:
    return save_book_argument_map(request.workspace, request.result)


@app.post("/review-cards")
def review_cards(request: ReviewCardRequest) -> dict[str, str]:
    return add_review_card(request.workspace, request.question, request.answer)


@app.post("/evidence-cards")
def evidence_cards(request: EvidenceCardRequest) -> dict[str, str]:
    return add_evidence_card(
        request.workspace,
        request.claim,
        request.locator,
        request.support,
        request.confidence,
        request.not_explicit,
        request.inference,
    )


@app.post("/obsidian-export")
def obsidian_export(request: ObsidianExportRequest) -> dict[str, object]:
    return export_obsidian(request.workspace, request.vault_folder)
