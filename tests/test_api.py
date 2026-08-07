import os
from pathlib import Path

import pytest
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


def test_import_workspace_endpoint_creates_workspace_from_upload(tmp_path: Path) -> None:
    client = TestClient(app)
    workspace = tmp_path / "uploaded-reading"

    response = client.post(
        "/workspaces/import",
        params={"filename": "uploaded.md", "workspace": str(workspace)},
        content=b"# Uploaded Chapter\n\nA short uploaded book.",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 200
    assert response.json()["workspace"] == str(workspace)
    assert (workspace / "metadata.json").exists()
    assert (workspace / "source_files" / "uploaded.md").exists()


def test_import_workspace_endpoint_rejects_empty_upload(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/workspaces/import",
        params={"filename": "empty.md", "workspace": str(tmp_path / "empty-reading")},
        content=b"",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Uploaded source is empty"


def test_import_workspace_endpoint_rolls_back_failed_upload(tmp_path: Path) -> None:
    client = TestClient(app)
    workspace = tmp_path / "failed-reading"

    response = client.post(
        "/workspaces/import",
        params={"filename": "unsupported.azw3", "workspace": str(workspace)},
        content=b"unsupported",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 400
    assert not workspace.exists()


def test_import_workspace_endpoint_preserves_existing_empty_target_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "existing-reading"
    workspace.mkdir()
    keep = workspace / "keep.txt"
    keep.write_text("keep", encoding="utf-8")

    def fail_build(*_args: object, **_kwargs: object) -> int:
        raise ValueError("synthetic extraction failure")

    monkeypatch.setattr("deep_reading.api.build_workspace", fail_build)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/workspaces/import",
        params={"filename": "uploaded.md", "workspace": str(workspace)},
        content=b"# Uploaded Chapter\n\nA short uploaded book.",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 500
    assert keep.read_text(encoding="utf-8") == "keep"
    assert not (workspace / "source_files").exists()


def test_import_workspace_endpoint_rejects_oversized_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("deep_reading.api.MAX_UPLOAD_BYTES", 4)
    client = TestClient(app)

    response = client.post(
        "/workspaces/import",
        params={"filename": "large.md", "workspace": str(tmp_path / "large-reading")},
        content=b"12345",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 400
    assert "size limit" in response.json()["error"]


def test_api_token_protects_local_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEP_READING_API_TOKEN", "test-token")
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/llm/providers").status_code == 401
    authorized = client.get(
        "/llm/providers",
        headers={"X-Deep-Reading-API-Token": "test-token"},
    )
    assert authorized.status_code == 200


def test_delete_workspace_endpoint_removes_initialized_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    workspace = tmp_path / "workspaces" / "delete-me"

    response = client.post(
        "/workspaces/import",
        params={"filename": "uploaded.md", "workspace": str(Path("workspaces/delete-me"))},
        content=b"# Uploaded Chapter\n\nA short uploaded book.",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 200

    delete_response = client.delete(
        "/workspaces",
        params={"workspace": str(Path("workspaces/delete-me"))},
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": "workspaces/delete-me"}
    assert not workspace.exists()


def test_delete_workspace_endpoint_rejects_paths_outside_workspaces(tmp_path: Path) -> None:
    client = TestClient(app)
    workspace = make_workspace(tmp_path)

    response = client.delete("/workspaces", params={"workspace": str(workspace)})

    assert response.status_code == 400
    assert response.json()["error"] == "Only workspaces under ./workspaces can be deleted"
    assert workspace.exists()


def test_llm_providers_endpoint_returns_reserved_provider_status() -> None:
    client = TestClient(app)

    response = client.get("/llm/providers")

    assert response.status_code == 200
    data = response.json()
    assert data["selected"] == "mock"
    providers = {item["name"]: item for item in data["providers"]}
    assert set(providers) == {"mock", "openai", "claude", "gemini", "deepseek", "qwen"}
    assert providers["openai"]["api_key_env"] == "OPENAI_API_KEY"
    assert providers["claude"]["api_key_env"] == "ANTHROPIC_API_KEY"
    assert providers["gemini"]["api_key_env"] == "GEMINI_API_KEY"
    assert providers["deepseek"]["api_key_env"] == "DEEPSEEK_API_KEY"
    assert providers["qwen"]["api_key_env"] == "QWEN_API_KEY"
    assert providers["openai"]["selected_env"] == "DEEP_READING_LLM_PROVIDER"


def test_llm_providers_endpoint_updates_selected_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEP_READING_LLM_PROVIDER", raising=False)
    client = TestClient(app)

    try:
        response = client.post("/llm/providers", json={"provider": "gemini"})

        assert response.status_code == 200
        data = response.json()
        assert data["selected"] == "gemini"
    finally:
        os.environ["DEEP_READING_LLM_PROVIDER"] = "mock"


def test_llm_providers_endpoint_rejects_unknown_provider() -> None:
    client = TestClient(app)

    response = client.post("/llm/providers", json={"provider": "unknown"})

    assert response.status_code == 400
    assert "Unsupported LLM provider" in response.json()["error"]


def test_llm_settings_endpoint_saves_runtime_config_without_returning_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEP_READING_LLM_SETTINGS_PATH", str(tmp_path / "settings.json"))
    monkeypatch.setenv("DEEP_READING_LLM_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post(
        "/llm/settings",
        json={
            "provider": "openai",
            "model": "gpt-saved",
            "base_url": "https://example.test/v1",
            "api_key": "saved-secret",
        },
    )

    assert response.status_code == 200
    data = response.json()
    providers = {item["name"]: item for item in data["providers"]}
    assert data["selected"] == "openai"
    assert providers["openai"]["api_key_present"] is True
    assert providers["openai"]["model"] == "gpt-saved"
    assert providers["openai"]["base_url"] == "https://example.test/v1"
    assert "saved-secret" not in str(data)


def test_llm_models_endpoint_returns_model_catalog() -> None:
    client = TestClient(app)

    response = client.get("/llm/models", params={"provider": "claude"})

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "claude"
    assert data["source"] == "fallback"
    assert data["reason"] == "recommended_only"
    assert data["models"][0]["value"] == "claude-opus-4-8"
    assert data["models"][1]["value"] == "claude-sonnet-4-6"


def test_llm_models_endpoint_rejects_unknown_provider() -> None:
    client = TestClient(app)

    response = client.get("/llm/models", params={"provider": "unknown"})

    assert response.status_code == 400
    assert "Unsupported LLM provider" in response.json()["error"]


def test_status_endpoint_returns_workspace_status(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.get("/status", params={"workspace": str(workspace)})

    assert response.status_code == 200
    data = response.json()
    assert data["workspace"] == str(workspace)
    assert data["current"] == "ch01"
    assert data["progress"] == {"not-started": 2}
    assert data["continue_reading"]["current_chapter"]["id"] == "ch01"
    assert data["continue_reading"]["next_action"]["kind"] == "start_next"


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
    assert "This is a short sample" in data["reading_guide"]["core_question"]
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


def test_state_endpoint_accepts_weak_state(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/state",
        json={"workspace": str(workspace), "chapter_id": "ch02", "state": "weak"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "weak"
    status = client.get("/status", params={"workspace": str(workspace)}).json()
    assert status["learning_loop"]["weak_chapters"][0]["id"] == "ch02"


def test_learning_loop_endpoint_returns_mastery_status(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    client.post(
        "/state",
        json={"workspace": str(workspace), "chapter_id": "ch01", "state": "done"},
    )

    response = client.get("/learning-loop", params={"workspace": str(workspace)})

    assert response.status_code == 200
    data = response.json()
    assert data["chapters"][0]["id"] == "ch01"
    assert data["chapters"][0]["mastery_score"] == 50
    assert data["weak_chapters"][0]["id"] == "ch01"
    assert data["review_ready"][0]["id"] == "ch01"


def test_learning_journal_endpoint_returns_saved_items(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/notes",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "section": "Confusions",
            "note_type": "Question",
            "text": "Why does this pattern matter?",
        },
    )
    assert response.status_code == 200

    response = client.get("/learning-journal", params={"workspace": str(workspace)})

    assert response.status_code == 200
    data = response.json()
    assert data["workspace"] == str(workspace)
    assert data["groups"]["question"] == 1
    assert data["items"][0]["kind"] == "question"
    assert data["items"][0]["editable"] is True


def test_learning_journal_item_update_and_delete_endpoints(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    client.post(
        "/notes",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "section": "Confusions",
            "note_type": "Question",
            "text": "Why does this pattern matter?",
        },
    )
    item = client.get("/learning-journal", params={"workspace": str(workspace)}).json()["items"][0]

    update_response = client.patch(
        "/learning-journal/item",
        json={
            "workspace": str(workspace),
            "item_id": item["id"],
            "content": "Why does this timing matter?",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "updated"
    updated = client.get("/learning-journal", params={"workspace": str(workspace)}).json()
    assert "Why does this timing matter?" in updated["items"][0]["content"]

    delete_response = client.request(
        "DELETE",
        "/learning-journal/item",
        json={"workspace": str(workspace), "item_id": item["id"]},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
    deleted = client.get("/learning-journal", params={"workspace": str(workspace)}).json()
    assert deleted["groups"].get("question") is None


def test_learning_journal_endpoint_rejects_missing_workspace(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.get("/learning-journal", params={"workspace": str(tmp_path / "missing")})

    assert response.status_code == 400
    assert "Workspace not found" in response.json()["error"]


def test_weak_concepts_endpoint_updates_learning_loop(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/weak-concepts",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "concept": "causal chain",
            "note": "Needs a better mechanism.",
        },
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "weak_concept"
    loop = client.get("/learning-loop", params={"workspace": str(workspace)}).json()
    assert loop["weak_concepts"][0]["concept"] == "causal chain"
    assert loop["weak_concepts"][0]["chapter_id"] == "ch01"


def test_weak_concepts_endpoint_rejects_empty_concept(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/weak-concepts",
        json={"workspace": str(workspace), "chapter_id": "ch01", "concept": " "},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Weak concept cannot be empty"


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


def test_feynman_check_endpoint_accepts_chinese_output_language(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/feynman-check",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "summary": "The chapter says many important things.",
            "language": "zh",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "因果链" in data["missing_causal_links"][0]
    assert "具体例子" in data["unsupported_leaps"][0]
    assert "为了让解释更有力" in data["rewritten_version"]


def test_selection_explanation_endpoint_returns_note_draft(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/selection-explanation",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "selected_text": "This is a short sample.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["chapter_id"] == "ch01"
    assert "How to read it:" in data["explanation"]


def test_selection_explanation_endpoint_accepts_output_language(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/selection-explanation",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "selected_text": "This is a short sample.",
            "language": "zh",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "怎么读这段" in data["explanation"]


def test_selection_review_question_endpoint_returns_card_draft(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/selection-review-question",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "selected_text": "This is a short sample.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["chapter_id"] == "ch01"
    assert "What claim or causal link" in data["question"]
    assert "This is a short sample." in data["answer"]


def test_chapter_synthesis_endpoint_returns_cross_chapter_prompts(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/chapter-synthesis",
        json={
            "workspace": str(workspace),
            "start_chapter_id": "ch01",
            "count": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["start_chapter_id"] == "ch01"
    assert data["chapter_count"] == 2
    assert [chapter["id"] for chapter in data["chapters"]] == ["ch01", "ch02"]
    assert data["recurring_concepts"]
    assert data["open_questions"]


def test_chapter_synthesis_endpoint_accepts_chinese_output_language(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/chapter-synthesis",
        json={
            "workspace": str(workspace),
            "start_chapter_id": "ch01",
            "count": 2,
            "language": "zh",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "共同澄清" in data["common_question"]
    assert "反复出现" in data["recurring_concepts"][0]


def test_book_argument_map_endpoint_returns_whole_book_structure(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post("/book-argument-map", json={"workspace": str(workspace)})

    assert response.status_code == 200
    data = response.json()
    assert data["chapter_count"] == 2
    assert [chapter["id"] for chapter in data["chapters"]] == ["ch01", "ch02"]
    assert data["argument_chain"]
    assert data["key_evidence"]


def test_save_book_argument_map_endpoint_appends_map(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    result = client.post("/book-argument-map", json={"workspace": str(workspace)}).json()

    response = client.post(
        "/book-argument-map/save",
        json={"workspace": str(workspace), "result": result},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "book_argument_map"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "## Whole-Book Argument Map" in content


def test_one_page_book_account_endpoint_returns_grounded_summary(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    client.post(
        "/state",
        json={"workspace": str(workspace), "chapter_id": "ch01", "state": "done"},
    )
    client.post(
        "/weak-concepts",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "concept": "causal chain",
        },
    )

    response = client.post("/one-page-book-account", json={"workspace": str(workspace)})

    assert response.status_code == 200
    data = response.json()
    assert data["chapter_count"] == 2
    assert data["completed_count"] == 1
    assert data["core_argument_chain"]
    assert any("causal chain" in item for item in data["weak_points"])


def test_save_one_page_book_account_endpoint_writes_markdown(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    result = client.post("/one-page-book-account", json={"workspace": str(workspace)}).json()

    response = client.post(
        "/one-page-book-account/save",
        json={"workspace": str(workspace), "result": result},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "one_page_book_account"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "# One-Page Book Account" in content


def test_active_recall_endpoint_returns_chapter_questions(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/active-recall",
        json={"workspace": str(workspace), "chapter_id": "ch01"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["chapter_id"] == "ch01"
    assert len(data["questions"]) == 3
    assert data["eligible_for_review"] is False


def test_active_recall_endpoint_accepts_chinese_output_language(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/active-recall",
        json={"workspace": str(workspace), "chapter_id": "ch01", "language": "zh"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "具体证据" in data["questions"][0]["answer_hint"]
    assert "整本书的大论证" in data["questions"][2]["question"]


def test_save_active_recall_endpoint_appends_review_cards(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    result = client.post(
        "/active-recall",
        json={"workspace": str(workspace), "chapter_id": "ch01"},
    ).json()

    response = client.post(
        "/active-recall/save",
        json={"workspace": str(workspace), "result": result},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "active_recall_cards"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "## Active Recall" in content


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


def test_evidence_table_endpoint_parses_saved_cards(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    client.post(
        "/evidence-cards",
        json={
            "workspace": str(workspace),
            "claim": "The chapter frames comparison.",
            "locator": "ch01: Intro",
            "support": "A source detail supports it.",
            "confidence": "High",
            "not_explicit": "It does not prove the whole book.",
            "inference": "This may guide later chapters.",
        },
    )

    response = client.post("/evidence-table", json={"workspace": str(workspace)})

    assert response.status_code == 200
    data = response.json()
    assert data["card_count"] == 1
    assert data["cards"][0]["claim"] == "The chapter frames comparison."
    assert data["cards"][0]["source_locator"] == "ch01: Intro"


def test_save_evidence_table_endpoint_writes_markdown(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    client.post(
        "/evidence-cards",
        json={
            "workspace": str(workspace),
            "claim": "Claim",
            "locator": "ch01: Intro",
            "support": "Support",
            "confidence": "Medium",
        },
    )
    result = client.post("/evidence-table", json={"workspace": str(workspace)}).json()

    response = client.post(
        "/evidence-table/save",
        json={"workspace": str(workspace), "result": result},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "evidence_table"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "# Evidence Table" in content
    assert "| Claim | ch01: Intro | Support | Medium | TBD | TBD |" in content


def test_concept_map_endpoint_returns_nodes_and_links(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    client.post(
        "/evidence-cards",
        json={
            "workspace": str(workspace),
            "claim": "Claim",
            "locator": "ch01: Intro",
            "support": "Support",
            "confidence": "Medium",
        },
    )
    client.post(
        "/weak-concepts",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "concept": "causal chain",
        },
    )

    response = client.post("/concept-map", json={"workspace": str(workspace)})

    assert response.status_code == 200
    data = response.json()
    assert data["node_count"] == 4
    assert any(node["type"] == "weak_concept" for node in data["nodes"])
    assert any(link["relation"] == "supports" for link in data["links"])


def test_save_concept_map_endpoint_writes_markdown(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    result = client.post("/concept-map", json={"workspace": str(workspace)}).json()

    response = client.post(
        "/concept-map/save",
        json={"workspace": str(workspace), "result": result},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "concept_map"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "# Concept Map" in content


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


def test_evidence_context_endpoint_returns_grounded_matches(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    client.post(
        "/evidence-cards",
        json={
            "workspace": str(workspace),
            "claim": "The chapter frames comparison.",
            "locator": "ch01: Intro",
            "support": "A source detail supports comparison.",
            "confidence": "High",
        },
    )

    response = client.post(
        "/evidence-context",
        json={
            "workspace": str(workspace),
            "chapter_id": "ch01",
            "query": "comparison",
            "limit": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "comparison"
    assert len(data["matches"]) <= 2
    assert {match["source_type"] for match in data["matches"]} & {"chapter", "evidence_card"}
    assert all(match["locator"] for match in data["matches"])


def test_evidence_context_endpoint_rejects_empty_query(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/evidence-context",
        json={"workspace": str(workspace), "query": " "},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Evidence context query cannot be empty"


def test_save_evidence_context_endpoint_writes_markdown(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)
    result = client.post(
        "/evidence-context",
        json={"workspace": str(workspace), "chapter_id": "ch01", "query": "short sample"},
    ).json()

    response = client.post(
        "/evidence-context/save",
        json={"workspace": str(workspace), "result": result},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "evidence_context"
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "**Query** short sample" in content


def test_obsidian_export_endpoint_exports_learning_archive_by_default(tmp_path: Path) -> None:
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
    assert data["mode"] == "learning_archive"
    assert data["markdown_files_exported"] > 0
    assert data["index_path"] == str(vault_folder / "Book Dashboard.md")
    assert (vault_folder / "Book Dashboard.md").exists()
    assert (vault_folder / "Review Queue.md").exists()
    assert (vault_folder / "Evidence Cards.md").exists()


def test_obsidian_export_endpoint_accepts_full_mode(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    vault_folder = tmp_path / "vault" / "reading"
    client = TestClient(app)

    response = client.post(
        "/obsidian-export",
        json={"workspace": str(workspace), "vault_folder": str(vault_folder), "mode": "full"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "full"
    assert data["index_path"] == str(vault_folder / "index.md")
    assert (vault_folder / "index.md").exists()


def test_obsidian_export_endpoint_rejects_unknown_mode(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/obsidian-export",
        json={
            "workspace": str(workspace),
            "vault_folder": str(tmp_path / "vault"),
            "mode": "unknown",
        },
    )

    assert response.status_code == 400
    assert "Unknown Obsidian export mode" in response.json()["error"]
