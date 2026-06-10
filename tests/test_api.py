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


def test_chapter_text_endpoint_returns_structured_error(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/chapter-text",
        params={"workspace": str(workspace), "chapter_id": "ch99"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "Unknown chapter: ch99"}
