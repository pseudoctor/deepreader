from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_llm_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEP_READING_LLM_SETTINGS_PATH", str(tmp_path / "llm_settings.json"))
    monkeypatch.setenv("DEEP_READING_LLM_PROVIDER", "mock")
