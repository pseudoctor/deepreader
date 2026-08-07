from deep_reading.chapters import detect_chapters, estimate_tokens, slugify


def test_estimate_tokens_counts_cjk_text_without_spaces() -> None:
    text = "中文阅读" * 50

    assert estimate_tokens(text) >= 200


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


def test_detect_chapters_finds_chinese_chapter_headings() -> None:
    text = """第 一 章 起源问题

正文。

第二章 农业与征服

更多正文。

第12章 现代世界

结尾。
"""

    assert detect_chapters(text) == [
        {"id": "ch01", "title": "起源问题", "line": 1},
        {"id": "ch02", "title": "农业与征服", "line": 5},
        {"id": "ch12", "title": "现代世界", "line": 9},
    ]


def test_detect_chapters_finds_chinese_numbered_headings() -> None:
    text = """一、问题的出现

正文。

二、证据的累积

正文。
"""

    assert detect_chapters(text) == [
        {"id": "ch01", "title": "问题的出现", "line": 1},
        {"id": "ch02", "title": "证据的累积", "line": 5},
    ]


def test_detect_chapters_relocates_table_of_contents_entries_to_body() -> None:
    text = """書名

目次

第一章 北國的進化

一、開國前的契丹

二、祖宗創業

第二章 多元體制

一、中央體制

二、大族與百姓

前言文字。

書名

一、開國前的契丹

正文第一章。

二、祖宗創業

正文。

書名

一、中央體制

正文第二章。

二、大族與百姓
"""

    assert detect_chapters(text) == [
        {"id": "ch01", "title": "北國的進化", "line": 21},
        {"id": "ch02", "title": "多元體制", "line": 31},
    ]


def test_detect_chapters_relocates_intro_chapter_outline_to_body() -> None:
    text = """目次

第一章 鴉片戰爭

一、朝貢貿易

第二章 內外躁動

一、英法聯軍

導言正文。

共有兩個章節安排如下：

第一章，鴉片戰爭

第二章，內外躁動

真正正文開始。

一、朝貢貿易

正文第一章。

一、英法聯軍

正文第二章。

C. F. Remer, The Foreign Trade of China, Shanghai: Commercial Press, 1926.
"""

    assert detect_chapters(text) == [
        {"id": "ch01", "title": "鴉片戰爭", "line": 21},
        {"id": "ch02", "title": "內外躁動", "line": 25},
    ]


def test_detect_chapters_finds_roman_numbered_headings() -> None:
    text = """I. Origins

Text.

II. Consequences

Text.
"""

    assert detect_chapters(text) == [
        {"id": "ch01", "title": "Origins", "line": 1},
        {"id": "ch02", "title": "Consequences", "line": 5},
    ]


def test_detect_chapters_falls_back_to_full_text() -> None:
    assert detect_chapters("No chapter headings here.") == [
        {"id": "ch01", "title": "Full Text", "line": 1}
    ]
