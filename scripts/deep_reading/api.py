"""FastAPI app exposing read-only workspace operations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from .errors import ExtractionError
from .service import get_status, list_chapters, read_chapter

WorkspaceQuery = Annotated[Path, Query()]
ChapterIdQuery = Annotated[str, Query()]


app = FastAPI(title="Deep Reading API", version="0.1.0")


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
