from pathlib import Path

from deep_reading.api import app
from deep_reading.cli import main
from fastapi.testclient import TestClient


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


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_endpoint_returns_workspace_status(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.get("/status", params={"workspace": str(workspace)})

    assert response.status_code == 200
    data = response.json()
    assert data["workspace"] == str(workspace)
    assert data["current"] == "ch01"
    assert data["progress"] == {"not-started": 2}


def test_chapters_endpoint_returns_chapter_list(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.get("/chapters", params={"workspace": str(workspace)})

    assert response.status_code == 200
    chapters = response.json()["chapters"]
    assert chapters[0]["id"] == "ch01"
    assert chapters[0]["title"] == "Intro"
    assert chapters[0]["state"] == "not-started"


def test_chapter_text_endpoint_returns_one_chapter(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/chapter-text",
        params={"workspace": str(workspace), "chapter_id": "ch01"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "ch01"
    assert "Chapter 1 Intro" in data["text"]
    assert "Chapter 2 Practice" not in data["text"]
    assert data["reading_guide"]["core_question"].startswith("What problem")
    assert "evidence" in data["reading_guide"]["evidence_to_seek"].casefold()
    assert "3-5 sentences" in data["reading_guide"]["recall_prompt"]


def test_chapter_text_endpoint_returns_structured_error(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/chapter-text",
        params={"workspace": str(workspace), "chapter_id": "ch99"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "Unknown chapter: ch99"}


def test_state_endpoint_updates_reading_state(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/state",
        json={"workspace": str(workspace), "chapter_id": "ch02", "state": "reading"},
    )

    assert response.status_code == 200
    assert response.json() == {"chapter_id": "ch02", "state": "reading", "current": "ch02"}
    chapters = client.get("/chapters", params={"workspace": str(workspace)}).json()["chapters"]
    assert chapters[1]["state"] == "reading"


def test_state_endpoint_returns_error_for_invalid_state(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/state",
        json={"workspace": str(workspace), "chapter_id": "ch01", "state": "invalid"},
    )

    assert response.status_code == 400
    assert response.json()["error"].startswith("Invalid state")


def test_notes_endpoint_appends_chapter_note(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/notes",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "section": "Confusions",
            "text": "I need to clarify the causal chain.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "chapter_note"
    assert data["chapter_id"] == "ch01"
    assert data["note_type"] == "My Thought"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "### My Thought" in content
    assert "I need to clarify the causal chain." in content


def test_notes_endpoint_appends_typed_quote(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/notes",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "section": "Key Concepts",
            "text": "This selected sentence matters.",
            "note_type": "Quote",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["note_type"] == "Quote"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "### Quote" in content
    assert "> This selected sentence matters." in content


def test_quotes_endpoint_appends_quote_to_chapter_note(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/quotes",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "quote": "This selected sentence matters.",
            "locator": "ch01: Intro",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "quote"
    assert data["chapter_id"] == "ch01"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "**Locator** ch01: Intro" in content
    assert "> This selected sentence matters." in content


def test_feynman_check_endpoint_returns_structured_feedback(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/feynman-check",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "summary": "The chapter says many important things. It compares societies.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["chapter_id"] == "ch01"
    assert data["vague_points"]
    assert data["missing_causal_links"]
    assert data["unsupported_leaps"]
    assert "causal mechanism" in data["rewritten_version"]


def test_review_cards_endpoint_appends_card(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/review-cards",
        json={
            "workspace": str(workspace),
            "question": "What is the chapter trying to answer?",
            "answer": "It frames the comparison problem.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "review_card"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "What is the chapter trying to answer?" in content
    assert "It frames the comparison problem." in content


def test_evidence_cards_endpoint_appends_card(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/evidence-cards",
        json={
            "workspace": str(workspace),
            "claim": "The chapter starts with a comparison problem.",
            "locator": "ch01",
            "support": "The opening asks why some societies gained advantages.",
            "confidence": "High",
            "not_explicit": "Exact causal path is not complete yet.",
            "inference": "This frames the book's research question.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "evidence_card"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "The chapter starts with a comparison problem." in content
    assert "**Confidence** High" in content


def test_obsidian_export_endpoint_exports_workspace_markdown(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    vault_folder = tmp_path / "vault" / "reading"
    client = TestClient(app)

    response = client.post(
        "/obsidian-export",
        json={"workspace": str(workspace), "vault_folder": str(vault_folder)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["vault_folder"] == str(vault_folder)
    assert data["markdown_files_exported"] > 0
    assert data["index_path"] == str(vault_folder / "index.md")
    assert (vault_folder / "index.md").exists()
    assert (vault_folder / "reading-plan.md").exists()
