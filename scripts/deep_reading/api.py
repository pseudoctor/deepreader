"""FastAPI app exposing read-only workspace operations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .errors import ExtractionError
from .service import (
    add_evidence_card,
    add_note,
    add_review_card,
    export_obsidian,
    get_status,
    list_chapters,
    read_chapter,
    update_reading_state,
)

WorkspaceQuery = Annotated[Path, Query()]
ChapterIdQuery = Annotated[str, Query()]


app = FastAPI(title="Deep Reading API", version="0.1.0")


class StateRequest(BaseModel):
    workspace: Path
    chapter_id: str
    state: str


class NoteRequest(BaseModel):
    workspace: Path
    chapter_id: str
    section: str
    text: str


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
    return add_note(request.workspace, request.chapter_id, request.section, request.text)


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
