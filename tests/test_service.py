from pathlib import Path

import pytest
from deep_reading.cli import main
from deep_reading.errors import ExtractionError
from deep_reading.service import (
    add_evidence_card,
    add_insight,
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
    build_reading_guide,
    check_feynman_summary,
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
    update_reading_state,
)


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


def test_list_chapters_returns_stateful_chapter_dicts(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    chapters = list_chapters(workspace)

    assert chapters[0] == {
        "id": "ch01",
        "title": "Intro",
        "line": chapters[0]["line"],
        "state": "not-started",
    }
    assert chapters[1] == {
        "id": "ch02",
        "title": "Practice",
        "line": chapters[1]["line"],
        "state": "not-started",
    }
    assert isinstance(chapters[0]["line"], int)
    assert isinstance(chapters[1]["line"], int)
    assert chapters[0]["line"] < chapters[1]["line"]


def test_get_status_returns_progress_and_artifacts(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    status = get_status(workspace)

    assert status["workspace"] == str(workspace)
    assert status["sources"] == 1
    assert status["current"] == "ch01"
    assert status["progress"] == {"not-started": 2}
    assert status["continue_reading"]["current_chapter"]["id"] == "ch01"
    assert status["continue_reading"]["next_action"]["kind"] == "start_next"
    assert status["continue_reading"]["next_action"]["chapter_id"] == "ch01"
    assert status["artifacts"]["evidence_cards.md"] is True


def test_get_status_prefers_done_chapters_for_review(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    update_reading_state(workspace, "ch01", "done")

    status = get_status(workspace)

    assert status["continue_reading"]["review_due"][0]["id"] == "ch01"
    assert status["continue_reading"]["next_action"] == {
        "kind": "review_completed",
        "chapter_id": "ch01",
        "title": "Intro",
    }


def test_get_status_includes_learning_loop_mastery(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    update_reading_state(workspace, "ch01", "done")
    add_note(workspace, "ch01", "Confusions", "This chapter needs a causal chain.")
    add_evidence_card(
        workspace,
        "Claim",
        "ch01: Intro",
        "A source detail.",
        "Medium",
    )
    recall = generate_active_recall(workspace, "ch01")
    save_active_recall_cards(workspace, recall)

    status = get_status(workspace)
    learning_loop = status["learning_loop"]
    chapter = learning_loop["chapters"][0]

    assert chapter["id"] == "ch01"
    assert chapter["mastery_score"] == 80
    assert chapter["has_notes"] is True
    assert chapter["has_active_recall"] is True
    assert chapter["has_evidence"] is True
    assert learning_loop["weak_chapters"] == []
    assert learning_loop["average_mastery"] == 40


def test_get_status_tracks_weak_chapters(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    update_reading_state(workspace, "ch02", "weak")
    status = get_status(workspace)
    learning_loop = status["learning_loop"]

    assert status["progress"]["weak"] == 1
    assert learning_loop["weak_chapters"][0]["id"] == "ch02"
    assert "Marked weak" in learning_loop["weak_chapters"][0]["weak_reasons"]
    assert learning_loop["review_ready"][0]["id"] == "ch02"


def test_add_weak_concept_updates_learning_loop(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = add_weak_concept(
        workspace,
        "causal chain",
        "ch01",
        "I can name the claim but not the mechanism.",
    )
    duplicate = add_weak_concept(workspace, "causal chain", "ch01", "Updated note.")
    status = get_status(workspace)
    weak_concepts = status["learning_loop"]["weak_concepts"]

    assert result["kind"] == "weak_concept"
    assert duplicate["note"] == "Updated note."
    assert len(weak_concepts) == 1
    assert weak_concepts[0]["concept"] == "causal chain"
    assert weak_concepts[0]["chapter_id"] == "ch01"
    assert (workspace / "learning_loop.json").exists()


def test_add_weak_concept_rejects_empty_concept(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    with pytest.raises(ExtractionError, match="Weak concept cannot be empty"):
        add_weak_concept(workspace, " ", "ch01")


def test_read_chapter_returns_structured_text(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    chapter = read_chapter(workspace, "ch01")

    assert chapter["id"] == "ch01"
    assert chapter["title"] == "Intro"
    assert "Chapter 1 Intro" in str(chapter["text"])
    assert "Chapter 2 Practice" not in str(chapter["text"])
    guide = chapter["reading_guide"]
    assert "This is a short sample" in guide["core_question"]
    assert "This is a short sample" in guide["evidence_to_seek"]
    assert "evidence" in guide["evidence_to_seek"].casefold()
    assert "3-5 sentences" in guide["recall_prompt"]


def test_build_reading_guide_uses_chinese_for_cjk_text() -> None:
    guide = build_reading_guide(
        "ch01",
        "导论",
        "为什么读书需要先提出问题？因为问题会改变我们寻找证据的方式。",
    )

    assert "阅读 ch01: 导论" in guide["core_question"]
    assert "具体证据" in guide["evidence_to_seek"]
    assert "3-5 句话" in guide["recall_prompt"]
    assert "What" not in guide["core_question"]


def test_synthesize_chapter_window_returns_cross_chapter_prompts(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = synthesize_chapter_window(workspace, "ch01", 2)

    assert result["start_chapter_id"] == "ch01"
    assert result["chapter_count"] == 2
    assert [chapter["id"] for chapter in result["chapters"]] == ["ch01", "ch02"]
    assert "jointly clarify" in str(result["common_question"])
    assert result["recurring_concepts"]
    assert "argument moves" in str(result["argument_progression"])
    assert result["open_questions"]


def test_synthesize_chapter_window_rejects_invalid_count(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    with pytest.raises(ExtractionError, match="Chapter count must be at least 1"):
        synthesize_chapter_window(workspace, "ch01", 0)


def test_build_book_argument_map_returns_whole_book_structure(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = build_book_argument_map(workspace)

    assert result["chapter_count"] == 2
    assert [chapter["id"] for chapter in result["chapters"]] == ["ch01", "ch02"]
    assert "central question" in str(result["core_problem"])
    assert "main answer" in str(result["core_answer"])
    assert result["argument_chain"]
    assert result["key_evidence"]
    assert result["rebuttals_and_limits"]


def test_save_book_argument_map_appends_to_argument_maps(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = build_book_argument_map(workspace)

    saved = save_book_argument_map(workspace, result)

    assert saved["kind"] == "book_argument_map"
    content = Path(saved["path"]).read_text(encoding="utf-8")
    assert "## Whole-Book Argument Map" in content
    assert "### Core Problem" in content
    assert "ch01: Intro" in content


def test_build_one_page_book_account_uses_learning_loop_inputs(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    update_reading_state(workspace, "ch01", "done")
    add_evidence_card(
        workspace,
        "The chapter frames comparison.",
        "ch01: Intro",
        "A source detail supports it.",
        "Medium",
    )
    add_weak_concept(workspace, "causal chain", "ch01", "Mechanism is still fuzzy.")

    result = build_one_page_book_account(workspace)

    assert result["chapter_count"] == 2
    assert result["completed_count"] == 1
    assert "workspace" in str(result["title"])
    assert "central problem" in str(result["core_account"])
    assert "Claim The chapter frames comparison." in result["strongest_evidence"]
    assert any("causal chain" in item for item in result["weak_points"])
    assert result["application_prompts"]


def test_save_one_page_book_account_writes_markdown(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = build_one_page_book_account(workspace)

    saved = save_one_page_book_account(workspace, result)

    assert saved["kind"] == "one_page_book_account"
    content = Path(saved["path"]).read_text(encoding="utf-8")
    assert "# One-Page Book Account" in content
    assert "## Core Argument Chain" in content
    assert "## Application Prompts" in content


def test_build_evidence_table_parses_evidence_cards(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    add_evidence_card(
        workspace,
        "The chapter frames comparison.",
        "ch01: Intro",
        "A source detail supports it.",
        "High",
        "It does not prove the whole book.",
        "This may guide later chapters.",
    )

    result = build_evidence_table(workspace)

    assert result["card_count"] == 1
    card = result["cards"][0]
    assert card["claim"] == "The chapter frames comparison."
    assert card["source_locator"] == "ch01: Intro"
    assert card["support"] == "A source detail supports it."
    assert card["confidence"] == "High"
    assert card["not_explicit"] == "It does not prove the whole book."
    assert card["inference"] == "This may guide later chapters."


def test_save_evidence_table_writes_markdown_table(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    add_evidence_card(workspace, "Claim", "ch01: Intro", "Support", "Medium")
    result = build_evidence_table(workspace)

    saved = save_evidence_table(workspace, result)

    assert saved["kind"] == "evidence_table"
    content = Path(saved["path"]).read_text(encoding="utf-8")
    assert "# Evidence Table" in content
    assert "| Claim | Source Locator | Support | Confidence | Not Explicit | Inference |" in content
    assert "| Claim | ch01: Intro | Support | Medium | TBD | TBD |" in content


def test_build_evidence_context_matches_chapter_text(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = build_evidence_context(workspace, "short sample", "ch01")

    assert result["query"] == "short sample"
    matches = result["matches"]
    assert matches
    assert matches[0]["source_type"] == "chapter"
    assert matches[0]["locator"] == "ch01: Intro"
    assert "short sample" in matches[0]["snippet"]


def test_build_evidence_context_matches_evidence_cards(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    add_evidence_card(
        workspace,
        "The chapter frames comparison.",
        "ch01: Intro",
        "A source detail supports comparison.",
        "High",
    )

    result = build_evidence_context(workspace, "frames comparison", "ch01")

    assert any(
        match["source_type"] == "evidence_card"
        and "frames comparison" in str(match["snippet"])
        for match in result["matches"]
    )


def test_build_evidence_context_rejects_empty_query(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    with pytest.raises(ExtractionError, match="Evidence context query cannot be empty"):
        build_evidence_context(workspace, " ")


def test_build_evidence_context_respects_limit(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = build_evidence_context(workspace, "chapter", limit=1)

    assert len(result["matches"]) == 1


def test_save_evidence_context_writes_grounded_markdown(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = build_evidence_context(workspace, "short sample", "ch01")

    saved = save_evidence_context(workspace, result)

    assert saved["kind"] == "evidence_context"
    content = Path(saved["path"]).read_text(encoding="utf-8")
    assert "## Evidence Context" in content
    assert "**Query** short sample" in content
    assert "**Locator** ch01: Intro" in content


def test_build_learning_journal_aggregates_saved_learning_content(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    add_note(workspace, "ch01", "Confusions", "Why does this comparison matter?", "Question")
    add_note(workspace, "ch01", "Key Concepts", "This is a short sample.", "Quote")
    add_review_card(workspace, "What changed?", "The reading became active.")
    add_evidence_card(workspace, "Claim", "ch01: Intro", "Support", "High")
    save_evidence_context(workspace, build_evidence_context(workspace, "short sample", "ch01"))
    add_weak_concept(workspace, "causal chain", "ch01", "Mechanism is fuzzy.")

    journal = build_learning_journal(workspace)
    kinds = {item["kind"] for item in journal["items"]}

    assert {
        "question",
        "quote",
        "review_card",
        "evidence_card",
        "evidence_context",
        "weak_concept",
    } <= kinds
    assert journal["groups"]["question"] == 1
    assert any("Why does this comparison matter?" in item["content"] for item in journal["items"])
    assert any(item["locator"] == "ch01: Intro" for item in journal["items"])


def test_build_learning_journal_handles_empty_optional_files(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    journal = build_learning_journal(workspace)

    assert journal["workspace"] == str(workspace)
    assert isinstance(journal["items"], list)
    assert isinstance(journal["groups"], dict)


def test_build_concept_map_uses_chapters_evidence_and_weak_concepts(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    update_reading_state(workspace, "ch01", "done")
    add_evidence_card(
        workspace,
        "The chapter frames comparison.",
        "ch01: Intro",
        "A source detail supports it.",
        "High",
    )
    add_weak_concept(workspace, "causal chain", "ch01", "Mechanism is fuzzy.")

    result = build_concept_map(workspace)

    node_types = {node["type"] for node in result["nodes"]}
    relations = {link["relation"] for link in result["links"]}
    labels = {node["label"] for node in result["nodes"]}
    assert result["node_count"] == 4
    assert "chapter" in node_types
    assert "evidence" in node_types
    assert "weak_concept" in node_types
    assert "supports" in relations
    assert "unclear_in" in relations
    assert "progresses_to" in relations
    assert "causal chain" in labels


def test_save_concept_map_writes_markdown(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = build_concept_map(workspace)

    saved = save_concept_map(workspace, result)

    assert saved["kind"] == "concept_map"
    content = Path(saved["path"]).read_text(encoding="utf-8")
    assert "# Concept Map" in content
    assert "## Nodes" in content
    assert "## Links" in content


def test_generate_active_recall_returns_chapter_questions(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = generate_active_recall(workspace, "ch01")

    assert result["chapter_id"] == "ch01"
    assert result["title"] == "Intro"
    assert len(result["questions"]) == 3
    assert result["eligible_for_review"] is False
    assert "main claim" in result["questions"][0]["answer_hint"]


def test_save_active_recall_cards_appends_review_cards(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = generate_active_recall(workspace, "ch01")

    saved = save_active_recall_cards(workspace, result)

    assert saved["kind"] == "active_recall_cards"
    content = Path(saved["path"]).read_text(encoding="utf-8")
    assert "## Active Recall" in content
    assert "**Chapter** ch01: Intro" in content
    assert "After reading, explain" in content


def test_check_feynman_summary_returns_structured_feedback(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = check_feynman_summary(
        workspace,
        "ch01",
        "The chapter says many important things. It compares societies.",
    )

    assert result["chapter_id"] == "ch01"
    assert result["title"] == "Intro"
    assert result["vague_points"]
    assert result["missing_causal_links"]
    assert result["unsupported_leaps"]
    assert "causal mechanism" in str(result["rewritten_version"])


def test_check_feynman_summary_rejects_empty_summary(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    with pytest.raises(ExtractionError, match="Summary cannot be empty"):
        check_feynman_summary(workspace, "ch01", " ")


def test_coach_action_reports_reserved_provider_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = make_workspace(tmp_path)
    monkeypatch.setenv("DEEP_READING_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ExtractionError, match="OPENAI_API_KEY"):
        check_feynman_summary(workspace, "ch01", "A short summary.")


def test_explain_selection_returns_note_ready_text(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = explain_selection(workspace, "ch01", "This is a short sample.")

    assert result["chapter_id"] == "ch01"
    assert result["title"] == "Intro"
    assert "What it says:" in result["explanation"]
    assert "This is a short sample." in result["explanation"]


def test_generate_selection_review_question_returns_card_draft(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = generate_selection_review_question(
        workspace,
        "ch01",
        "This is a short sample.",
    )

    assert result["chapter_id"] == "ch01"
    assert "What claim or causal link" in result["question"]
    assert "This is a short sample." in result["answer"]


def test_selection_actions_use_chinese_templates_for_chinese_text(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    explanation = explain_selection(workspace, "ch01", "這段文字支持一個因果推論。")
    review = generate_selection_review_question(workspace, "ch01", "這段文字支持一個因果推論。")

    assert "怎么读这段" in explanation["explanation"]
    assert "支持了什么主张或因果链" in review["question"]


def test_selection_actions_can_force_chinese_for_english_text(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    explanation = explain_selection(
        workspace,
        "ch01",
        "This is a short sample.",
        language="zh",
    )
    review = generate_selection_review_question(
        workspace,
        "ch01",
        "This is a short sample.",
        language="zh",
    )

    assert "怎么读这段" in explanation["explanation"]
    assert "支持了什么主张或因果链" in review["question"]


def test_selection_actions_reject_empty_text(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    with pytest.raises(ExtractionError, match="Selected text cannot be empty"):
        explain_selection(workspace, "ch01", " ")
    with pytest.raises(ExtractionError, match="Selected text cannot be empty"):
        generate_selection_review_question(workspace, "ch01", " ")


def test_update_reading_state_writes_state_file(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = update_reading_state(workspace, "ch02", "reading")

    assert result == {"chapter_id": "ch02", "state": "reading", "current": "ch02"}
    assert list_chapters(workspace)[1]["state"] == "reading"


def test_update_reading_state_rejects_invalid_state(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    with pytest.raises(ExtractionError, match="Invalid state"):
        update_reading_state(workspace, "ch01", "invalid")


def test_add_note_returns_written_path(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = add_note(workspace, "ch01", "Confusions", "What is the main distinction?")

    assert result["kind"] == "chapter_note"
    assert result["chapter_id"] == "ch01"
    assert result["note_type"] == "My Thought"
    assert Path(result["path"]).exists()
    content = Path(result["path"]).read_text(encoding="utf-8")
    assert "### My Thought" in content
    assert "What is the main distinction?" in content


def test_add_note_supports_quote_type(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = add_note(
        workspace,
        "ch01",
        "Key Concepts",
        "This selected sentence matters.",
        "Quote",
    )

    assert result["note_type"] == "Quote"
    content = Path(result["path"]).read_text(encoding="utf-8")
    assert "### Quote" in content
    assert "> This selected sentence matters." in content


def test_add_quote_appends_selected_text_to_chapter_note(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    result = add_quote(
        workspace,
        "ch01",
        "This selected sentence matters.",
        "ch01: Intro",
    )

    assert result["kind"] == "quote"
    assert result["chapter_id"] == "ch01"
    content = Path(result["path"]).read_text(encoding="utf-8")
    assert "## Quote" in content
    assert "**Locator** ch01: Intro" in content
    assert "> This selected sentence matters." in content


def test_add_insight_review_and_evidence_cards_return_paths(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    insight = add_insight(workspace, "This applies to my research workflow.")
    review = add_review_card(workspace, "What changed?", "The reading process became active.")
    evidence = add_evidence_card(
        workspace,
        claim="The chapter frames the core problem.",
        locator="ch01",
        support="The opening question defines the comparison.",
        confidence="High",
    )

    assert Path(insight["path"]).exists()
    assert Path(review["path"]).exists()
    assert Path(evidence["path"]).exists()
    assert "This applies to my research workflow." in Path(insight["path"]).read_text(
        encoding="utf-8"
    )
    assert "What changed?" in Path(review["path"]).read_text(encoding="utf-8")
    assert "The chapter frames the core problem." in Path(evidence["path"]).read_text(
        encoding="utf-8"
    )


def test_export_obsidian_returns_structured_result(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    vault_folder = tmp_path / "vault"

    result = export_obsidian(workspace, vault_folder)

    assert result["vault_folder"] == str(vault_folder)
    assert result["markdown_files_exported"] > 0
    assert Path(str(result["index_path"])).exists()
    assert "book_map.md" in result["files"]
