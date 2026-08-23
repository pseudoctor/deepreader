import builtins
from pathlib import Path

import pytest
from deep_reading import sources
from deep_reading.errors import ExtractionError
from deep_reading.sources import (
    extract_docx,
    extract_html,
    extract_pdf,
    extract_rtf,
    resolve_sources,
)


def test_resolve_sources_accepts_single_supported_file(tmp_path: Path) -> None:
    source = tmp_path / "book.md"
    source.write_text("# Chapter 1\n", encoding="utf-8")

    assert resolve_sources(str(source)) == [source.resolve()]


def test_resolve_sources_filters_supported_files_in_directory(tmp_path: Path) -> None:
    supported = tmp_path / "book.txt"
    unsupported = tmp_path / "cover.png"
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_supported = nested / "chapter.md"

    supported.write_text("text", encoding="utf-8")
    unsupported.write_text("image", encoding="utf-8")
    nested_supported.write_text("chapter", encoding="utf-8")

    assert resolve_sources(str(tmp_path)) == [
        supported.resolve(),
        nested_supported.resolve(),
    ]


def test_resolve_sources_accepts_glob(tmp_path: Path) -> None:
    first = tmp_path / "a.md"
    second = tmp_path / "b.txt"
    ignored = tmp_path / "c.png"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    ignored.write_text("c", encoding="utf-8")

    assert resolve_sources(str(tmp_path / "*")) == [
        first.resolve(),
        second.resolve(),
    ]


def test_resolve_sources_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ExtractionError, match="Source not found"):
        resolve_sources(str(tmp_path / "missing.md"))


def test_resolve_sources_rejects_directory_without_supported_files(tmp_path: Path) -> None:
    (tmp_path / "cover.png").write_text("image", encoding="utf-8")

    with pytest.raises(ExtractionError, match="No supported files found"):
        resolve_sources(str(tmp_path))


def test_extract_html_skips_script_style_and_keeps_body_text(tmp_path: Path) -> None:
    source = tmp_path / "page.html"
    source.write_text(
        """
        <html>
          <head><style>.hidden { color: red; }</style></head>
          <body>
            <h1>Visible Title</h1>
            <script>alert("skip me")</script>
            <p>First paragraph.</p>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    result = extract_html(source)

    assert result.method == "html.parser"
    assert "Visible Title" in result.text
    assert "First paragraph." in result.text
    assert "skip me" not in result.text
    assert "hidden" not in result.text


def test_extract_html_keeps_skipping_inside_nested_hidden_elements(tmp_path: Path) -> None:
    source = tmp_path / "nested.html"
    source.write_text(
        "<noscript>hidden<style>also hidden</style>still hidden</noscript><p>Visible</p>",
        encoding="utf-8",
    )

    result = extract_html(source)

    assert result.text == "Visible"


def test_extract_rtf_uses_regex_fallback_when_striprtf_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.rtf"
    source.write_text(r"{\rtf1\ansi Bold text}", encoding="utf-8")
    original_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name.startswith("striprtf"):
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = extract_rtf(source)

    assert result.method == "rtf-regex"
    assert "Bold text" in result.text


def test_extract_docx_reports_extraction_error_when_fallback_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "broken.docx"
    source.write_text("not a zip", encoding="utf-8")
    original_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "docx":
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ExtractionError, match="Could not extract DOCX"):
        extract_docx(source)


def test_extract_pdf_reports_clear_error_when_extractors_are_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"%PDF broken")
    original_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "PyPDF2" or name.startswith("pdfminer"):
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(sources.shutil, "which", lambda name: None)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ExtractionError, match="Could not extract PDF"):
        extract_pdf(source)
