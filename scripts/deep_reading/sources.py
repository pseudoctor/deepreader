"""Source discovery and text extraction helpers."""

from __future__ import annotations

import glob
import html.parser
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from .errors import ExtractionError
from .models import SourceResult

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".epub",
    ".docx",
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".rtf",
}


TEXT_EXTENSIONS = {".txt", ".text", ".md", ".markdown"}


class HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
        if tag in {"p", "br", "div", "section", "article", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "div", "section", "article", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            cleaned = re.sub(r"\s+", " ", data).strip()
            if cleaned:
                self.parts.append(cleaned + " ")

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self.parts)).strip()


def resolve_sources(source: str) -> list[Path]:
    p = Path(source).expanduser()
    files: list[Path] = []
    if any(ch in source for ch in "*?["):
        matches = glob.glob(os.path.expanduser(source), recursive=True)
        files = [
            Path(x).resolve()
            for x in sorted(matches)
            if Path(x).is_file() and Path(x).suffix.lower() in SUPPORTED_EXTENSIONS
        ]
    elif p.is_dir():
        for root, _, names in os.walk(p):
            for name in names:
                candidate = Path(root) / name
                if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                    files.append(candidate.resolve())
        files.sort(key=lambda item: str(item).lower())
    elif p.is_file():
        files = [p.resolve()]
    else:
        raise ExtractionError(f"Source not found: {source}")
    if not files:
        raise ExtractionError(f"No supported files found in: {source}")
    return files


def extract_text_file(path: Path) -> SourceResult:
    return SourceResult(
        path=path, text=path.read_text(encoding="utf-8", errors="replace"), method="plain-text"
    )


def extract_html(path: Path) -> SourceResult:
    parser = HTMLTextExtractor()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return SourceResult(path=path, text=parser.text(), method="html.parser")


def extract_docx(path: Path) -> SourceResult:
    try:
        import docx  # type: ignore

        document = docx.Document(str(path))
        text = "\n\n".join(p.text for p in document.paragraphs if p.text.strip())
        return SourceResult(path=path, text=text, method="python-docx")
    except ImportError:
        pass
    try:
        with zipfile.ZipFile(path) as zf:
            raw = zf.read("word/document.xml").decode("utf-8", errors="replace")
        raw = re.sub(r"</w:p>", "\n", raw)
        raw = re.sub(r"<[^>]+>", "", raw)
        return SourceResult(path=path, text=raw, method="docx-zip-xml")
    except Exception as exc:
        raise ExtractionError(f"Could not extract DOCX {path.name}: {exc}") from exc


def extract_rtf(path: Path) -> SourceResult:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        from striprtf.striprtf import rtf_to_text  # type: ignore

        return SourceResult(path=path, text=rtf_to_text(raw), method="striprtf")
    except ImportError:
        text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
        text = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
        text = re.sub(r"[{}]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return SourceResult(path=path, text=text, method="rtf-regex")


def extract_pdf(path: Path) -> SourceResult:
    if shutil.which("pdftotext"):
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return SourceResult(
                path=path, text=result.stdout, method="pdftotext", pages=count_pdf_pages(path)
            )
    try:
        import PyPDF2  # type: ignore

        parts = []
        with path.open("rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                parts.append(page.extract_text() or "")
        text = "\n\n".join(parts)
        if text.strip():
            return SourceResult(path=path, text=text, method="PyPDF2", pages=len(reader.pages))
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text  # type: ignore

        text = extract_text(str(path))
        if text.strip():
            return SourceResult(
                path=path, text=text, method="pdfminer.six", pages=count_pdf_pages(path)
            )
    except Exception:
        pass
    raise ExtractionError(
        f"Could not extract PDF {path.name}. Install poppler, PyPDF2, or pdfminer.six."
    )


def count_pdf_pages(path: Path) -> int:
    if shutil.which("pdfinfo"):
        result = subprocess.run(
            ["pdfinfo", str(path)], capture_output=True, text=True, timeout=15, check=False
        )
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                try:
                    return int(line.split(":", 1)[1].strip())
                except ValueError:
                    return 0
    return 0


def extract_epub(path: Path) -> SourceResult:
    try:
        import ebooklib  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
        from ebooklib import epub  # type: ignore

        book = epub.read_epub(str(path))
        parts = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            parts.append(soup.get_text(separator="\n"))
        return SourceResult(path=path, text="\n\n".join(parts), method="ebooklib")
    except Exception:
        pass
    try:
        with zipfile.ZipFile(path) as zf:
            names = sorted(n for n in zf.namelist() if n.endswith((".html", ".xhtml")))
            parts = []
            for name in names:
                parser = HTMLTextExtractor()
                parser.feed(zf.read(name).decode("utf-8", errors="replace"))
                parts.append(parser.text())
        return SourceResult(path=path, text="\n\n".join(parts), method="epub-zipfile")
    except Exception as exc:
        raise ExtractionError(f"Could not extract EPUB {path.name}: {exc}") from exc


def extract_source(path: Path) -> SourceResult:
    ext = path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return extract_text_file(path)
    if ext in {".html", ".htm"}:
        return extract_html(path)
    if ext == ".docx":
        return extract_docx(path)
    if ext == ".rtf":
        return extract_rtf(path)
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".epub":
        return extract_epub(path)
    raise ExtractionError(f"Unsupported file type: {path.name}")
