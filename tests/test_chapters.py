from deep_reading.chapters import detect_chapters, slugify


def test_slugify_normalizes_to_filesystem_safe_slug() -> None:
    assert slugify("Chapter 1: Intro & Setup") == "chapter-1-intro-setup"
    assert slugify("!!!") == "reading-workspace"


def test_detect_chapters_finds_markdown_chapter_headings() -> None:
    text = """# Chapter 1 Intro

Some text.

## Chapter 2 Practice

More text.
"""

    assert detect_chapters(text) == [
        {"id": "ch01", "title": "Intro", "line": 1},
        {"id": "ch02", "title": "Practice", "line": 5},
    ]


def test_detect_chapters_falls_back_to_full_text() -> None:
    assert detect_chapters("No chapter headings here.") == [
        {"id": "ch01", "title": "Full Text", "line": 1}
    ]
