import json
import os
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest
from deep_reading.llm import (
    build_provider,
    configured_provider_name,
    list_provider_models,
    list_provider_status,
    load_llm_settings,
    save_llm_settings,
    set_configured_provider_name,
    update_llm_settings,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_list_provider_status_includes_reserved_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEP_READING_LLM_PROVIDER", raising=False)

    status = list_provider_status()

    assert status["selected"] == "mock"
    providers = {item["name"]: item for item in status["providers"]}
    assert set(providers) == {"mock", "openai", "claude", "gemini", "deepseek", "qwen"}
    assert providers["mock"]["configured"] is True
    assert providers["openai"]["api_key_env"] == "OPENAI_API_KEY"
    assert providers["claude"]["api_key_env"] == "ANTHROPIC_API_KEY"
    assert providers["gemini"]["api_key_env"] == "GEMINI_API_KEY"
    assert providers["deepseek"]["api_key_env"] == "DEEPSEEK_API_KEY"
    assert providers["qwen"]["api_key_env"] == "QWEN_API_KEY"
    assert providers["openai"]["model"] == "gpt-5.4-mini"
    assert providers["claude"]["model"] == "claude-sonnet-4-6"
    assert providers["gemini"]["model"] == "gemini-3.5-flash"
    assert providers["deepseek"]["model"] == "deepseek-chat"
    assert providers["openai"]["fallback_models"][0]["value"] == "gpt-5.5"
    assert providers["openai"]["fallback_models"][1]["value"] == "gpt-5.4"


def test_provider_status_detects_api_key_without_exposing_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")

    status = list_provider_status()

    openai = next(item for item in status["providers"] if item["name"] == "openai")
    assert openai["configured"] is True
    assert openai["api_key_present"] is True
    assert "secret-value" not in str(openai)


def test_saved_provider_settings_override_environment_without_exposing_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEP_READING_LLM_SETTINGS_PATH", str(tmp_path / "settings.json"))
    monkeypatch.setenv("DEEP_READING_LLM_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    status = update_llm_settings(
        "openai",
        model="gpt-saved",
        base_url="https://example.test/v1",
        api_key="saved-secret",
    )

    providers = {item["name"]: item for item in status["providers"]}
    assert status["selected"] == "openai"
    assert configured_provider_name() == "openai"
    assert providers["openai"]["configured"] is True
    assert providers["openai"]["model"] == "gpt-saved"
    assert providers["openai"]["base_url"] == "https://example.test/v1"
    assert "saved-secret" not in str(status)


def test_llm_settings_recover_from_corrupt_file_and_save_private_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = tmp_path / "settings.json"
    monkeypatch.setenv("DEEP_READING_LLM_SETTINGS_PATH", str(settings))
    settings.write_text("{not-json", encoding="utf-8")

    assert load_llm_settings() == {"selected": None, "providers": {}}

    save_llm_settings({"selected": "mock", "providers": {}})

    assert settings.stat().st_mode & 0o777 == 0o600


def test_configured_provider_falls_back_to_mock_for_unknown_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEP_READING_LLM_PROVIDER", "unknown")

    assert configured_provider_name() == "mock"


def test_provider_requires_configured_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    provider = build_provider("qwen")

    with pytest.raises(RuntimeError, match="QWEN_API_KEY"):
        provider.complete_json("prompt", "schema")


def test_set_configured_provider_name_updates_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEP_READING_LLM_PROVIDER", raising=False)

    try:
        selected = set_configured_provider_name("claude")

        assert selected == "claude"
        assert configured_provider_name() == "claude"
    finally:
        os.environ["DEEP_READING_LLM_PROVIDER"] = "mock"


def test_list_provider_models_returns_recommended_for_claude() -> None:
    result = list_provider_models("claude")

    assert result["source"] == "fallback"
    assert result["reason"] == "recommended_only"
    assert result["models"][0]["value"] == "claude-opus-4-8"  # type: ignore[index]
    assert result["models"][1]["value"] == "claude-sonnet-4-6"  # type: ignore[index]


def test_list_provider_models_falls_back_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = list_provider_models("openai")

    assert result["source"] == "fallback"
    assert result["reason"] == "auth"
    assert result["models"][0]["value"] == "gpt-5.5"  # type: ignore[index]
    assert result["models"][1]["value"] == "gpt-5.4"  # type: ignore[index]


def test_list_provider_models_fetches_openai_compatible_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: int) -> FakeResponse:
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        captured["headers"] = dict(req.header_items())  # type: ignore[attr-defined]
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "data": [
                    {"id": "gpt-4o-mini", "created": 100},
                    {"id": "gpt-5.2", "created": 110},
                    {"id": "gpt-5.4-mini", "created": 120},
                    {"id": "embedding-small", "created": 130},
                ]
            }
        )

    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setattr("deep_reading.llm.request.urlopen", fake_urlopen)

    result = list_provider_models("openai")

    assert result["source"] == "remote"
    assert captured["url"] == "https://api.openai.com/v1/models"
    assert captured["timeout"] == 20
    assert captured["headers"]["Authorization"].endswith("secret-value")  # type: ignore[index]
    assert [item["value"] for item in result["models"][:3]] == [  # type: ignore[index]
        "gpt-5.4-mini",
        "gpt-5.2",
        "gpt-4o-mini",
    ]
    assert "secret-value" not in str(result)


def test_list_provider_models_fetches_gemini_base_model_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: int) -> FakeResponse:
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        captured["headers"] = dict(req.header_items())  # type: ignore[attr-defined]
        assert timeout == 20
        return FakeResponse(
            {
                "models": [
                    {
                        "name": "models/gemini-2.5-flash",
                        "baseModelId": "gemini-2.5-flash",
                        "displayName": "Gemini 2.5 Flash",
                    },
                    {
                        "name": "models/gemini-2.5-flash-preview-tts",
                        "baseModelId": "gemini-2.5-flash-preview-tts",
                        "displayName": "Gemini TTS",
                    },
                    {
                        "name": "models/gemini-3-flash-preview",
                        "baseModelId": "gemini-3-flash-preview",
                        "displayName": "Gemini 3 Flash Preview",
                    },
                ]
            }
        )

    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    monkeypatch.setattr("deep_reading.llm.request.urlopen", fake_urlopen)

    result = list_provider_models("gemini")

    assert result["source"] == "remote"
    assert str(captured["url"]).startswith("https://generativelanguage.googleapis.com/v1beta/models")
    assert "gemini-secret" not in str(captured["url"])
    assert "gemini-secret" in str(captured["headers"])
    assert [item["value"] for item in result["models"]] == [  # type: ignore[index]
        "gemini-2.5-flash",
        "gemini-3-flash-preview",
    ]
    assert "tts" not in str(result)
    assert "gemini-secret" not in str(result)


def test_mock_provider_runs_feynman_check() -> None:
    provider = build_provider("mock")

    result = provider.check_feynman_summary(
        {"id": "ch01", "title": "Intro"},
        "The chapter says many important things. It compares societies.",
    )

    assert result["chapter_id"] == "ch01"
    assert result["vague_points"]
    assert result["missing_causal_links"]
    assert result["unsupported_leaps"]


def test_mock_provider_explains_selection() -> None:
    provider = build_provider("mock")

    result = provider.explain_selection(
        {"id": "ch01", "title": "Intro"},
        "This is a short sample.",
    )

    assert result["chapter_id"] == "ch01"
    assert "How to read it:" in result["explanation"]


def test_mock_provider_explains_selection_in_requested_language() -> None:
    provider = build_provider("mock")

    result = provider.explain_selection(
        {"id": "ch01", "title": "Intro"},
        "This is a short sample.",
        language="zh",
    )

    assert "怎么读这段" in result["explanation"]


def test_mock_provider_generates_selection_review_question() -> None:
    provider = build_provider("mock")

    result = provider.generate_selection_review_question(
        {"id": "ch01", "title": "Intro"},
        "This is a short sample.",
    )

    assert result["chapter_id"] == "ch01"
    assert "What claim or causal link" in result["question"]


def test_openai_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    provider = build_provider("openai")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        provider.check_feynman_summary({"id": "ch01", "title": "Intro"}, "summary")


def test_openai_provider_posts_structured_responses_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: int) -> FakeResponse:
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        captured["headers"] = dict(req.header_items())  # type: ignore[attr-defined]
        captured["body"] = json.loads(req.data.decode("utf-8"))  # type: ignore[attr-defined]
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "output_text": json.dumps(
                    {
                        "accurate_points": ["Names a causal mechanism."],
                        "vague_points": [],
                        "missing_causal_links": [],
                        "unsupported_leaps": [],
                        "rewritten_version": "A clearer version.",
                    }
                )
            }
        )

    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("DEEP_READING_OPENAI_BASE_URL", "https://example.test/v1/")
    monkeypatch.setattr("deep_reading.llm.request.urlopen", fake_urlopen)

    provider = build_provider("openai")
    result = provider.check_feynman_summary(
        {"id": "ch01", "title": "Intro", "evidence_context": "GROUNDING_MARKER"},
        "The chapter explains the claim because it cites evidence.",
    )

    body = captured["body"]
    headers = captured["headers"]
    assert result["chapter_id"] == "ch01"
    assert result["title"] == "Intro"
    assert result["rewritten_version"] == "A clearer version."
    assert captured["url"] == "https://example.test/v1/responses"
    assert captured["timeout"] == 60
    assert body["model"] == "gpt-test"  # type: ignore[index]
    assert body["text"]["format"]["type"] == "json_schema"  # type: ignore[index]
    assert body["text"]["format"]["strict"] is True  # type: ignore[index]
    assert "GROUNDING_MARKER" in json.dumps(body)
    assert headers["Authorization"].endswith("secret-value")  # type: ignore[index]
    assert "secret-value" not in json.dumps(body)


def test_openai_provider_parses_output_content_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(_req: object, timeout: int) -> FakeResponse:
        assert timeout == 60
        return FakeResponse(
            {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "question": "What is the claim?",
                                        "answer": "The passage supports the main claim.",
                                    }
                                ),
                            }
                        ]
                    }
                ]
            }
        )

    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setattr("deep_reading.llm.request.urlopen", fake_urlopen)

    provider = build_provider("openai")
    result = provider.generate_selection_review_question(
        {"id": "ch01", "title": "Intro"},
        "This passage supports a claim with evidence.",
    )

    assert result["chapter_id"] == "ch01"
    assert result["question"] == "What is the claim?"


def test_openai_provider_reports_http_error_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(_req: object, timeout: int) -> FakeResponse:
        assert timeout == 60
        raise HTTPError(
            url="https://example.test/v1/responses",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=BytesIO(b'{"error":{"message":"Invalid model"}}'),
        )

    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setattr("deep_reading.llm.request.urlopen", fake_urlopen)

    provider = build_provider("openai")
    with pytest.raises(RuntimeError) as excinfo:
        provider.explain_selection({"id": "ch01", "title": "Intro"}, "Selected text.")

    message = str(excinfo.value)
    assert "status 400" in message
    assert "Invalid model" in message
    assert "secret-value" not in message


def test_claude_provider_uses_messages_tool_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: int) -> FakeResponse:
        assert timeout == 60
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        captured["headers"] = dict(req.header_items())  # type: ignore[attr-defined]
        captured["body"] = json.loads(req.data.decode("utf-8"))  # type: ignore[attr-defined]
        return FakeResponse(
            {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "return_json",
                        "input": {"explanation": "A concise explanation."},
                    }
                ]
            }
        )

    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-value")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")
    monkeypatch.setenv("DEEP_READING_CLAUDE_BASE_URL", "https://claude.test/v1")
    monkeypatch.setattr("deep_reading.llm.request.urlopen", fake_urlopen)

    provider = build_provider("claude")
    result = provider.explain_selection(
        {"id": "ch01", "title": "Intro"},
        "Selected text.",
        language="zh",
    )

    body = captured["body"]
    headers = captured["headers"]
    assert result["explanation"] == "A concise explanation."
    assert captured["url"] == "https://claude.test/v1/messages"
    assert body["model"] == "claude-test"  # type: ignore[index]
    assert body["tool_choice"]["name"] == "return_json"  # type: ignore[index]
    assert body["tools"][0]["input_schema"]["required"] == ["explanation"]  # type: ignore[index]
    assert "Output language: Chinese" in body["messages"][0]["content"]  # type: ignore[index]
    assert headers["X-api-key"] == "secret-value"  # type: ignore[index]
    assert "secret-value" not in json.dumps(body)


def test_gemini_provider_uses_generate_content_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: int) -> FakeResponse:
        assert timeout == 60
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        captured["headers"] = dict(req.header_items())  # type: ignore[attr-defined]
        captured["body"] = json.loads(req.data.decode("utf-8"))  # type: ignore[attr-defined]
        return FakeResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "question": "What changed?",
                                            "answer": "The evidence changed.",
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setenv("GEMINI_API_KEY", "secret-value")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("DEEP_READING_GEMINI_BASE_URL", "https://gemini.test/v1beta")
    monkeypatch.setattr("deep_reading.llm.request.urlopen", fake_urlopen)

    provider = build_provider("gemini")
    result = provider.generate_selection_review_question(
        {"id": "ch01", "title": "Intro"},
        "Selected text.",
    )

    body = captured["body"]
    assert result["question"] == "What changed?"
    assert captured["url"] == "https://gemini.test/v1beta/models/gemini-test:generateContent"
    assert body["generationConfig"]["response_mime_type"] == "application/json"  # type: ignore[index]
    assert body["generationConfig"]["response_json_schema"]["required"] == [  # type: ignore[index]
        "question",
        "answer",
    ]


@pytest.mark.parametrize(
    ("provider_name", "api_key_env", "base_url_env", "expected_url"),
    [
        ("deepseek", "DEEPSEEK_API_KEY", "DEEP_READING_DEEPSEEK_BASE_URL", "https://deepseek.test/chat/completions"),
        ("qwen", "QWEN_API_KEY", "DEEP_READING_QWEN_BASE_URL", "https://qwen.test/chat/completions"),
    ],
)
def test_openai_compatible_provider_uses_chat_completions(
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    api_key_env: str,
    base_url_env: str,
    expected_url: str,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: int) -> FakeResponse:
        assert timeout == 60
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        captured["body"] = json.loads(req.data.decode("utf-8"))  # type: ignore[attr-defined]
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "accurate_points": ["Accurate"],
                                    "vague_points": [],
                                    "missing_causal_links": [],
                                    "unsupported_leaps": [],
                                    "rewritten_version": "Clearer.",
                                }
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setenv(api_key_env, "secret-value")
    monkeypatch.setenv(base_url_env, expected_url.removesuffix("/chat/completions"))
    monkeypatch.setattr("deep_reading.llm.request.urlopen", fake_urlopen)

    provider = build_provider(provider_name)
    result = provider.check_feynman_summary({"id": "ch01", "title": "Intro"}, "Summary.")

    body = captured["body"]
    assert result["rewritten_version"] == "Clearer."
    assert captured["url"] == expected_url
    assert body["response_format"] == {"type": "json_object"}  # type: ignore[index]
    assert "feynman_check" in json.dumps(body)
