"""FastAPI app exposing read-only workspace operations."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .chapters import slugify
from .errors import ExtractionError
from .llm import (
    list_provider_models,
    list_provider_status,
    set_configured_provider_name,
    update_llm_settings,
)
from .service import (
    add_evidence_card,
    add_note,
    add_quote,
    add_review_card,
    add_weak_concept,
    build_book_argument_map,
    build_concept_map,
    build_evidence_context,
    build_evidence_table,
    build_learning_journal,
    build_one_page_book_account,
    check_feynman_summary,
    delete_learning_journal_item,
    explain_selection,
    export_obsidian,
    generate_active_recall,
    generate_selection_review_question,
    get_status,
    list_chapters,
    read_chapter,
    save_active_recall_cards,
    save_book_argument_map,
    save_concept_map,
    save_evidence_context,
    save_evidence_table,
    save_one_page_book_account,
    synthesize_chapter_window,
    update_learning_journal_item,
    update_reading_state,
)
from .workspace import build_workspace

WorkspaceQuery = Annotated[Path, Query()]
ChapterIdQuery = Annotated[str, Query()]


app = FastAPI(title="Deep Reading API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://127.0.0.1:5174", "null"],
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


class LearningJournalUpdateRequest(BaseModel):
    workspace: Path
    item_id: str
    content: str


class LearningJournalDeleteRequest(BaseModel):
    workspace: Path
    item_id: str


class FeynmanCheckRequest(BaseModel):
    workspace: Path
    chapter_id: str
    summary: str
    language: str | None = None


class SelectionActionRequest(BaseModel):
    workspace: Path
    chapter_id: str
    selected_text: str
    language: str | None = None


class ChapterSynthesisRequest(BaseModel):
    workspace: Path
    start_chapter_id: str
    count: int = Field(default=3, ge=1, le=10)
    language: str | None = None


class BookArgumentMapRequest(BaseModel):
    workspace: Path
    language: str | None = None


class SaveBookArgumentMapRequest(BaseModel):
    workspace: Path
    result: dict[str, object]


class SaveOnePageBookAccountRequest(BaseModel):
    workspace: Path
    result: dict[str, object]


class SaveEvidenceTableRequest(BaseModel):
    workspace: Path
    result: dict[str, object]


class SaveConceptMapRequest(BaseModel):
    workspace: Path
    result: dict[str, object]


class ActiveRecallRequest(BaseModel):
    workspace: Path
    chapter_id: str
    language: str | None = None


class SaveActiveRecallRequest(BaseModel):
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


class EvidenceContextRequest(BaseModel):
    workspace: Path
    query: str
    chapter_id: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SaveEvidenceContextRequest(BaseModel):
    workspace: Path
    result: dict[str, object]


class WeakConceptRequest(BaseModel):
    workspace: Path
    chapter_id: str
    concept: str
    note: str = ""


class ObsidianExportRequest(BaseModel):
    workspace: Path
    vault_folder: Path
    mode: str = "learning_archive"


class LLMProviderRequest(BaseModel):
    provider: str


class LLMSettingsRequest(BaseModel):
    provider: str
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


def upload_workspace_for(filename: str, workspace: Path | None) -> Path:
    if workspace is not None:
        return workspace
    stem = Path(filename).stem or "reading-workspace"
    return Path("workspaces") / f"{slugify(stem)}-reading"


def safe_upload_filename(filename: str) -> str:
    name = Path(filename).name
    return name or "source.txt"


def resolve_deletable_workspace(workspace: Path) -> Path:
    root = Path("workspaces").resolve()
    target = workspace.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ExtractionError("Only workspaces under ./workspaces can be deleted") from exc
    if not target.exists():
        raise ExtractionError(f"Workspace does not exist: {workspace}")
    if not target.is_dir():
        raise ExtractionError(f"Workspace is not a directory: {workspace}")
    if not (target / "metadata.json").exists():
        raise ExtractionError(f"Not an initialized workspace: {workspace}")
    return target


@app.exception_handler(ExtractionError)
async def extraction_error_handler(request, exc: ExtractionError) -> JSONResponse:  # noqa: ANN001
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.delete("/workspaces")
def delete_workspace(workspace: WorkspaceQuery) -> dict[str, str]:
    target = resolve_deletable_workspace(workspace)
    shutil.rmtree(target)
    return {"deleted": str(workspace)}


@app.post("/workspaces/import")
async def import_workspace(
    request: Request,
    filename: Annotated[str, Query(min_length=1)],
    workspace: Annotated[Path | None, Query()] = None,
) -> dict[str, str]:
    content = await request.body()
    if not content:
        raise ExtractionError("Uploaded source is empty")
    target_workspace = upload_workspace_for(filename, workspace)
    if (target_workspace / "metadata.json").exists():
        raise ExtractionError(f"Workspace already exists: {target_workspace}")
    source_file = target_workspace / "source_files" / safe_upload_filename(filename)
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(content)
    build_workspace(str(source_file), target_workspace)
    return {"workspace": str(target_workspace)}


@app.get("/llm/providers")
def llm_providers() -> dict[str, object]:
    return list_provider_status()


@app.post("/llm/providers")
def update_llm_provider(request: LLMProviderRequest) -> dict[str, object]:
    try:
        set_configured_provider_name(request.provider)
    except ValueError as exc:
        raise ExtractionError(str(exc)) from exc
    return list_provider_status()


@app.get("/llm/settings")
def llm_settings() -> dict[str, object]:
    return list_provider_status()


@app.get("/llm/models")
def llm_models(provider: str) -> dict[str, object]:
    try:
        return list_provider_models(provider)
    except ValueError as exc:
        raise ExtractionError(str(exc)) from exc


@app.post("/llm/settings")
def update_settings(request: LLMSettingsRequest) -> dict[str, object]:
    try:
        return update_llm_settings(
            request.provider,
            request.model,
            request.base_url,
            request.api_key,
        )
    except ValueError as exc:
        raise ExtractionError(str(exc)) from exc


@app.get("/status")
def status(workspace: WorkspaceQuery) -> dict[str, object]:
    return get_status(workspace)


@app.get("/learning-loop")
def learning_loop(workspace: WorkspaceQuery) -> dict[str, object]:
    return get_status(workspace)["learning_loop"]  # type: ignore[return-value]


@app.get("/learning-journal")
def learning_journal(workspace: WorkspaceQuery) -> dict[str, object]:
    return build_learning_journal(workspace)


@app.patch("/learning-journal/item")
def learning_journal_update(request: LearningJournalUpdateRequest) -> dict[str, object]:
    return update_learning_journal_item(request.workspace, request.item_id, request.content)


@app.api_route("/learning-journal/item", methods=["DELETE"])
async def learning_journal_delete(request: Request) -> dict[str, object]:
    payload = await request.json()
    parsed = LearningJournalDeleteRequest.model_validate(payload)
    return delete_learning_journal_item(parsed.workspace, parsed.item_id)


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
    return check_feynman_summary(
        request.workspace,
        request.chapter_id,
        request.summary,
        request.language,
    )


@app.post("/selection-explanation")
def selection_explanation(request: SelectionActionRequest) -> dict[str, str]:
    return explain_selection(
        request.workspace,
        request.chapter_id,
        request.selected_text,
        request.language,
    )


@app.post("/selection-review-question")
def selection_review_question(request: SelectionActionRequest) -> dict[str, str]:
    return generate_selection_review_question(
        request.workspace,
        request.chapter_id,
        request.selected_text,
        request.language,
    )


@app.post("/chapter-synthesis")
def chapter_synthesis(request: ChapterSynthesisRequest) -> dict[str, object]:
    return synthesize_chapter_window(
        request.workspace,
        request.start_chapter_id,
        request.count,
        request.language,
    )


@app.post("/book-argument-map")
def book_argument_map(request: BookArgumentMapRequest) -> dict[str, object]:
    return build_book_argument_map(request.workspace, request.language)


@app.post("/book-argument-map/save")
def save_argument_map(request: SaveBookArgumentMapRequest) -> dict[str, str]:
    return save_book_argument_map(request.workspace, request.result)


@app.post("/one-page-book-account")
def one_page_book_account(request: BookArgumentMapRequest) -> dict[str, object]:
    return build_one_page_book_account(request.workspace, request.language)


@app.post("/one-page-book-account/save")
def save_book_account(request: SaveOnePageBookAccountRequest) -> dict[str, str]:
    return save_one_page_book_account(request.workspace, request.result)


@app.post("/active-recall")
def active_recall(request: ActiveRecallRequest) -> dict[str, object]:
    return generate_active_recall(request.workspace, request.chapter_id, request.language)


@app.post("/active-recall/save")
def save_active_recall(request: SaveActiveRecallRequest) -> dict[str, str]:
    return save_active_recall_cards(request.workspace, request.result)


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


@app.post("/evidence-context")
def evidence_context(request: EvidenceContextRequest) -> dict[str, object]:
    return build_evidence_context(
        request.workspace,
        request.query,
        request.chapter_id,
        request.limit,
    )


@app.post("/evidence-context/save")
def save_context(request: SaveEvidenceContextRequest) -> dict[str, str]:
    return save_evidence_context(request.workspace, request.result)


@app.post("/evidence-table")
def evidence_table(request: BookArgumentMapRequest) -> dict[str, object]:
    return build_evidence_table(request.workspace, request.language)


@app.post("/evidence-table/save")
def save_table(request: SaveEvidenceTableRequest) -> dict[str, str]:
    return save_evidence_table(request.workspace, request.result)


@app.post("/concept-map")
def concept_map(request: BookArgumentMapRequest) -> dict[str, object]:
    return build_concept_map(request.workspace, request.language)


@app.post("/concept-map/save")
def save_map(request: SaveConceptMapRequest) -> dict[str, str]:
    return save_concept_map(request.workspace, request.result)


@app.post("/weak-concepts")
def weak_concepts(request: WeakConceptRequest) -> dict[str, object]:
    return add_weak_concept(
        request.workspace,
        request.concept,
        request.chapter_id,
        request.note,
    )


@app.post("/obsidian-export")
def obsidian_export(request: ObsidianExportRequest) -> dict[str, object]:
    return export_obsidian(request.workspace, request.vault_folder, request.mode)
