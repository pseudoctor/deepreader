import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Chapter = {
  id: string;
  title: string;
  line: number;
  state: string;
};

type Status = {
  workspace: string;
  sources: number;
  words: number;
  estimated_tokens: number;
  current: string | null;
  progress: Record<string, number>;
  artifacts: Record<string, boolean>;
};

type ChapterText = {
  id: string;
  title: string;
  line: number;
  text: string;
};

type ObsidianExportResult = {
  vault_folder: string;
  markdown_files_exported: number;
  index_path: string;
  files: string[];
};

type SelectionToolbarPosition = {
  left: number;
  top: number;
};

type DeepReadingDesktopApi = {
  apiBaseUrl: string;
  platform: string;
  selectWorkspaceFolder: () => Promise<string | null>;
  selectObsidianFolder: () => Promise<string | null>;
};

declare global {
  interface Window {
    deepReadingDesktop?: DeepReadingDesktopApi;
  }
}

const defaultWorkspace = "workspaces/guns-germs-steel-reading";

type Language = "en" | "zh";

const languages: { code: Language; label: string }[] = [
  { code: "en", label: "EN" },
  { code: "zh", label: "中文" },
];

const noteSectionOptions = [
  "Confusions",
  "Key Concepts",
  "My 3-5 Sentence Summary",
  "Applications",
] as const;

const confidenceOptions = ["High", "Medium", "Low"] as const;

const stateOptions = ["reading", "done", "review"] as const;

const translations = {
  en: {
    appTitle: "Deep Reading",
    appSubtitle: "Workspace reader",
    language: "Language",
    workspace: "Workspace",
    selectWorkspace: "Choose folder",
    load: "Load",
    recentWorkspaces: "Recent workspaces",
    noRecentWorkspaces: "No recent workspaces yet",
    status: "Status",
    export: "Export",
    obsidianFolder: "Obsidian folder",
    selectObsidianFolder: "Choose folder",
    obsidianFolderPlaceholder: "/Users/me/ObsidianVault/Reading/book-name",
    exportToObsidian: "Export to Obsidian",
    noWorkspaceLoaded: "No workspace loaded",
    chapters: "Chapters",
    chapter: "Chapter",
    noChapter: "No chapter",
    emptyReader: "Load a workspace to start reading.",
    capture: "Capture",
    buildUnderstanding: "Build understanding",
    captureType: "Capture type",
    note: "Note",
    review: "Review",
    evidence: "Evidence",
    selectedText: "Selected text",
    saveQuote: "Save quote",
    makeEvidenceCard: "Make evidence card",
    section: "Section",
    notePlaceholder: "Write a question, summary, or application...",
    saveNote: "Save note",
    question: "Question",
    reviewQuestionPlaceholder: "What should future me recall?",
    answer: "Answer",
    reviewAnswerPlaceholder: "Write the answer in your own words...",
    saveReviewCard: "Save review card",
    claim: "Claim",
    claimPlaceholder: "What claim does this passage support?",
    locator: "Locator",
    support: "Support",
    supportPlaceholder: "Use a brief paraphrase or short excerpt...",
    confidence: "Confidence",
    notExplicit: "Not explicit",
    notExplicitPlaceholder: "What does the source not prove?",
    myInference: "My inference",
    inferencePlaceholder: "What are you inferring from it?",
    saveEvidenceCard: "Save evidence card",
    working: "Working...",
    workspaceLoaded: "Workspace loaded",
    noteSaved: "Note saved",
    reviewCardSaved: "Review card saved",
    evidenceCardSaved: "Evidence card saved",
    quoteSaved: "Quote saved",
    obsidianExported: "Exported {count} Markdown files to {folder}",
    failedLoadWorkspace: "Failed to load workspace",
    failedLoadChapter: "Failed to load chapter",
    failedSelectWorkspace: "Failed to choose workspace folder",
    failedSelectObsidianFolder: "Failed to choose Obsidian folder",
    failedUpdateState: "Failed to update state",
    failedSaveNote: "Failed to save note",
    failedSaveReviewCard: "Failed to save review card",
    failedSaveEvidenceCard: "Failed to save evidence card",
    failedSaveQuote: "Failed to save quote",
    failedObsidianExport: "Failed to export to Obsidian",
    requestFailed: "Request failed",
    marked: "marked",
    stateLabels: {
      reading: "reading",
      done: "done",
      review: "review",
    },
    noteSectionLabels: {
      Confusions: "Confusions",
      "Key Concepts": "Key Concepts",
      "My 3-5 Sentence Summary": "My 3-5 Sentence Summary",
      Applications: "Applications",
    },
    confidenceLabels: {
      High: "High",
      Medium: "Medium",
      Low: "Low",
    },
  },
  zh: {
    appTitle: "深度阅读",
    appSubtitle: "工作区阅读器",
    language: "语言",
    workspace: "工作区",
    selectWorkspace: "选择文件夹",
    load: "载入",
    recentWorkspaces: "最近工作区",
    noRecentWorkspaces: "暂无最近工作区",
    status: "状态",
    export: "导出",
    obsidianFolder: "Obsidian 文件夹",
    selectObsidianFolder: "选择文件夹",
    obsidianFolderPlaceholder: "/Users/me/ObsidianVault/Reading/book-name",
    exportToObsidian: "导出到 Obsidian",
    noWorkspaceLoaded: "尚未载入工作区",
    chapters: "章节",
    chapter: "章节",
    noChapter: "未选择章节",
    emptyReader: "载入一个工作区后开始阅读。",
    capture: "记录",
    buildUnderstanding: "构建理解",
    captureType: "记录类型",
    note: "笔记",
    review: "复习卡",
    evidence: "证据卡",
    selectedText: "已选文本",
    saveQuote: "保存摘录",
    makeEvidenceCard: "转为证据卡",
    section: "分类",
    notePlaceholder: "写下问题、总结或可应用之处...",
    saveNote: "保存笔记",
    question: "问题",
    reviewQuestionPlaceholder: "未来的我需要回忆什么？",
    answer: "答案",
    reviewAnswerPlaceholder: "用自己的话写下答案...",
    saveReviewCard: "保存复习卡",
    claim: "主张",
    claimPlaceholder: "这段内容支持了什么主张？",
    locator: "位置",
    support: "证据",
    supportPlaceholder: "写简短转述或短摘录...",
    confidence: "可信度",
    notExplicit: "未明说",
    notExplicitPlaceholder: "原文没有证明什么？",
    myInference: "我的推论",
    inferencePlaceholder: "你从中推论出了什么？",
    saveEvidenceCard: "保存证据卡",
    working: "处理中...",
    workspaceLoaded: "工作区已载入",
    noteSaved: "笔记已保存",
    reviewCardSaved: "复习卡已保存",
    evidenceCardSaved: "证据卡已保存",
    quoteSaved: "摘录已保存",
    obsidianExported: "已导出 {count} 个 Markdown 文件到 {folder}",
    failedLoadWorkspace: "载入工作区失败",
    failedLoadChapter: "载入章节失败",
    failedSelectWorkspace: "选择工作区文件夹失败",
    failedSelectObsidianFolder: "选择 Obsidian 文件夹失败",
    failedUpdateState: "更新状态失败",
    failedSaveNote: "保存笔记失败",
    failedSaveReviewCard: "保存复习卡失败",
    failedSaveEvidenceCard: "保存证据卡失败",
    failedSaveQuote: "保存摘录失败",
    failedObsidianExport: "导出到 Obsidian 失败",
    requestFailed: "请求失败",
    marked: "标记为",
    stateLabels: {
      reading: "阅读中",
      done: "已完成",
      review: "复习",
    },
    noteSectionLabels: {
      Confusions: "困惑",
      "Key Concepts": "关键概念",
      "My 3-5 Sentence Summary": "我的 3-5 句总结",
      Applications: "可应用之处",
    },
    confidenceLabels: {
      High: "高",
      Medium: "中",
      Low: "低",
    },
  },
} satisfies Record<Language, Record<string, unknown>>;

function getInitialLanguage(): Language {
  const storedLanguage = window.localStorage.getItem("deep-reading-language");
  return storedLanguage === "zh" ? "zh" : "en";
}

function getInitialObsidianFolder(): string {
  return window.localStorage.getItem("deep-reading-obsidian-folder") ?? "";
}

function getInitialRecentWorkspaces(): string[] {
  try {
    const stored = window.localStorage.getItem("deep-reading-recent-workspaces");
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string").slice(0, 5)
      : [];
  } catch {
    return [];
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const apiBaseUrl = window.deepReadingDesktop?.apiBaseUrl ?? "/api";
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data as T;
}

function App() {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const t = translations[language];
  const [workspace, setWorkspace] = useState(defaultWorkspace);
  const [status, setStatus] = useState<Status | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [activeChapter, setActiveChapter] = useState<ChapterText | null>(null);
  const [activeCapture, setActiveCapture] = useState<"note" | "review" | "evidence">("note");
  const [noteSection, setNoteSection] = useState("Confusions");
  const [noteText, setNoteText] = useState("");
  const [reviewQuestion, setReviewQuestion] = useState("");
  const [reviewAnswer, setReviewAnswer] = useState("");
  const [evidenceClaim, setEvidenceClaim] = useState("");
  const [evidenceLocator, setEvidenceLocator] = useState("");
  const [evidenceSupport, setEvidenceSupport] = useState("");
  const [evidenceConfidence, setEvidenceConfidence] = useState("Medium");
  const [evidenceNotExplicit, setEvidenceNotExplicit] = useState("");
  const [evidenceInference, setEvidenceInference] = useState("");
  const [selectedText, setSelectedText] = useState("");
  const [selectionToolbarPosition, setSelectionToolbarPosition] =
    useState<SelectionToolbarPosition | null>(null);
  const [obsidianFolder, setObsidianFolder] = useState(getInitialObsidianFolder);
  const [recentWorkspaces, setRecentWorkspaces] = useState<string[]>(getInitialRecentWorkspaces);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    window.localStorage.setItem("deep-reading-language", language);
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [language]);

  useEffect(() => {
    window.localStorage.setItem("deep-reading-obsidian-folder", obsidianFolder);
  }, [obsidianFolder]);

  useEffect(() => {
    window.localStorage.setItem(
      "deep-reading-recent-workspaces",
      JSON.stringify(recentWorkspaces),
    );
  }, [recentWorkspaces]);

  const progressText = useMemo(() => {
    if (!status) return t.noWorkspaceLoaded;
    return Object.entries(status.progress)
      .map(([key, value]) => `${key}: ${value}`)
      .join(" · ");
  }, [status, t.noWorkspaceLoaded]);

  useEffect(() => {
    document.addEventListener("selectionchange", handleTextSelection);
    return () => document.removeEventListener("selectionchange", handleTextSelection);
  });

  async function loadWorkspace(nextWorkspace = workspace) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const query = new URLSearchParams({ workspace: nextWorkspace });
      const [nextStatus, chapterResult] = await Promise.all([
        apiRequest<Status>(`/status?${query.toString()}`),
        apiRequest<{ chapters: Chapter[] }>(`/chapters?${query.toString()}`),
      ]);
      setStatus(nextStatus);
      setChapters(chapterResult.chapters);
      if (chapterResult.chapters.length > 0) {
        await loadChapter(chapterResult.chapters[0].id, nextWorkspace);
      }
      setRecentWorkspaces((current) => [
        nextWorkspace,
        ...current.filter((item) => item !== nextWorkspace),
      ].slice(0, 5));
      setMessage(t.workspaceLoaded);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedLoadWorkspace);
    } finally {
      setBusy(false);
    }
  }

  async function selectWorkspaceFolder() {
    if (!window.deepReadingDesktop) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const selectedWorkspace = await window.deepReadingDesktop.selectWorkspaceFolder();
      if (!selectedWorkspace) return;
      setWorkspace(selectedWorkspace);
      await loadWorkspace(selectedWorkspace);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSelectWorkspace);
    } finally {
      setBusy(false);
    }
  }

  async function selectObsidianFolder() {
    if (!window.deepReadingDesktop) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const selectedFolder = await window.deepReadingDesktop.selectObsidianFolder();
      if (!selectedFolder) return;
      setObsidianFolder(selectedFolder);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSelectObsidianFolder);
    } finally {
      setBusy(false);
    }
  }

  async function loadChapter(chapterId: string, currentWorkspace = workspace) {
    setBusy(true);
    setError("");
    try {
      const query = new URLSearchParams({ workspace: currentWorkspace, chapter_id: chapterId });
      const chapter = await apiRequest<ChapterText>(`/chapter-text?${query.toString()}`);
      setActiveChapter(chapter);
      setEvidenceLocator(`${chapter.id}: ${chapter.title}`);
      setSelectedText("");
      setSelectionToolbarPosition(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedLoadChapter);
    } finally {
      setBusy(false);
    }
  }

  function handleTextSelection() {
    if (!activeChapter) return;
    const selection = window.getSelection();
    const text = selection?.toString().trim() ?? "";
    if (!selection || text.length === 0 || selection.rangeCount === 0) {
      setSelectedText("");
      setSelectionToolbarPosition(null);
      return;
    }

    const range = selection.getRangeAt(0);
    const container =
      range.commonAncestorContainer.nodeType === Node.TEXT_NODE
        ? range.commonAncestorContainer.parentElement
        : (range.commonAncestorContainer as Element);
    if (!container?.closest(".chapter-text")) {
      setSelectedText("");
      setSelectionToolbarPosition(null);
      return;
    }

    const rect = range.getBoundingClientRect();
    setSelectedText(text);
    setSelectionToolbarPosition({
      left: Math.min(Math.max(rect.left + rect.width / 2, 120), window.innerWidth - 120),
      top: Math.max(rect.top - 52, 12),
    });
  }

  async function saveSelectedQuote() {
    if (!activeChapter || !selectedText.trim()) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/quotes", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: activeChapter.id,
          quote: selectedText.trim(),
          locator: `${activeChapter.id}: ${activeChapter.title}`,
        }),
      });
      setMessage(t.quoteSaved);
      setSelectedText("");
      setSelectionToolbarPosition(null);
      window.getSelection()?.removeAllRanges();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveQuote);
    } finally {
      setBusy(false);
    }
  }

  function sendSelectionToEvidenceCard() {
    if (!activeChapter || !selectedText.trim()) return;
    setActiveCapture("evidence");
    setEvidenceLocator(`${activeChapter.id}: ${activeChapter.title}`);
    setEvidenceSupport(selectedText.trim());
    setSelectedText("");
    setSelectionToolbarPosition(null);
    window.getSelection()?.removeAllRanges();
  }

  async function updateState(nextState: string) {
    if (!activeChapter) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/state", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: activeChapter.id,
          state: nextState,
        }),
      });
      await loadWorkspace(workspace);
      await loadChapter(activeChapter.id, workspace);
      setMessage(`${activeChapter.id} ${t.marked} ${t.stateLabels[nextState as keyof typeof t.stateLabels]}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedUpdateState);
    } finally {
      setBusy(false);
    }
  }

  async function saveNote(event: FormEvent) {
    event.preventDefault();
    if (!activeChapter || !noteText.trim()) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/notes", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: activeChapter.id,
          section: noteSection,
          text: noteText.trim(),
        }),
      });
      setNoteText("");
      setMessage(t.noteSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveNote);
    } finally {
      setBusy(false);
    }
  }

  async function saveReviewCard(event: FormEvent) {
    event.preventDefault();
    if (!reviewQuestion.trim() || !reviewAnswer.trim()) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/review-cards", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          question: reviewQuestion.trim(),
          answer: reviewAnswer.trim(),
        }),
      });
      setReviewQuestion("");
      setReviewAnswer("");
      setMessage(t.reviewCardSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveReviewCard);
    } finally {
      setBusy(false);
    }
  }

  async function saveEvidenceCard(event: FormEvent) {
    event.preventDefault();
    if (!evidenceClaim.trim() || !evidenceLocator.trim() || !evidenceSupport.trim()) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/evidence-cards", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          claim: evidenceClaim.trim(),
          locator: evidenceLocator.trim(),
          support: evidenceSupport.trim(),
          confidence: evidenceConfidence,
          not_explicit: evidenceNotExplicit.trim() || "TBD",
          inference: evidenceInference.trim() || "TBD",
        }),
      });
      setEvidenceClaim("");
      setEvidenceSupport("");
      setEvidenceNotExplicit("");
      setEvidenceInference("");
      setMessage(t.evidenceCardSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveEvidenceCard);
    } finally {
      setBusy(false);
    }
  }

  async function exportToObsidian(event: FormEvent) {
    event.preventDefault();
    if (!obsidianFolder.trim()) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await apiRequest<ObsidianExportResult>("/obsidian-export", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          vault_folder: obsidianFolder.trim(),
        }),
      });
      setMessage(
        t.obsidianExported
          .replace("{count}", String(result.markdown_files_exported))
          .replace("{folder}", result.vault_folder),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedObsidianExport);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <header className="brand">
          <span className="brand-mark">DR</span>
          <div>
            <h1>{t.appTitle}</h1>
            <p>{t.appSubtitle}</p>
          </div>
        </header>

        <div className="language-switcher" aria-label={t.language}>
          {languages.map((option) => (
            <button
              key={option.code}
              className={language === option.code ? "active" : ""}
              onClick={() => {
                setLanguage(option.code);
                setMessage("");
                setError("");
              }}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>

        <form
          className="workspace-form"
          onSubmit={(event) => {
            event.preventDefault();
            void loadWorkspace();
          }}
        >
          <label htmlFor="workspace">{t.workspace}</label>
          <input
            id="workspace"
            value={workspace}
            onChange={(event) => setWorkspace(event.target.value)}
            spellCheck={false}
          />
          {window.deepReadingDesktop && (
            <button type="button" onClick={() => void selectWorkspaceFolder()} disabled={busy}>
              {t.selectWorkspace}
            </button>
          )}
          <button type="submit" disabled={busy}>
            {t.load}
          </button>
        </form>

        <div className="recent-workspaces">
          <span className="eyebrow">{t.recentWorkspaces}</span>
          {recentWorkspaces.length === 0 ? (
            <p className="muted">{t.noRecentWorkspaces}</p>
          ) : (
            <div className="recent-workspace-list">
              {recentWorkspaces.map((recentWorkspace) => (
                <button
                  key={recentWorkspace}
                  onClick={() => {
                    setWorkspace(recentWorkspace);
                    void loadWorkspace(recentWorkspace);
                  }}
                  type="button"
                  disabled={busy}
                  title={recentWorkspace}
                >
                  {recentWorkspace}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="status-block">
          <span>{t.status}</span>
          <strong>{progressText}</strong>
        </div>

        <form className="export-form" onSubmit={exportToObsidian}>
          <span className="eyebrow">{t.export}</span>
          <label htmlFor="obsidian-folder">{t.obsidianFolder}</label>
          <input
            id="obsidian-folder"
            value={obsidianFolder}
            onChange={(event) => setObsidianFolder(event.target.value)}
            placeholder={t.obsidianFolderPlaceholder}
            spellCheck={false}
          />
          {window.deepReadingDesktop && (
            <button type="button" onClick={() => void selectObsidianFolder()} disabled={busy}>
              {t.selectObsidianFolder}
            </button>
          )}
          <button type="submit" disabled={busy || !obsidianFolder.trim()}>
            {t.exportToObsidian}
          </button>
        </form>

        <nav className="chapter-list" aria-label={t.chapters}>
          {chapters.map((chapter) => (
            <button
              key={chapter.id}
              className={activeChapter?.id === chapter.id ? "active" : ""}
              onClick={() => void loadChapter(chapter.id)}
              type="button"
            >
              <span>{chapter.id}</span>
              <strong>{chapter.title}</strong>
              <em>{t.stateLabels[chapter.state as keyof typeof t.stateLabels] ?? chapter.state}</em>
            </button>
          ))}
        </nav>
      </aside>

      <section className="reader-pane">
        {selectionToolbarPosition && selectedText && (
          <div
            className="selection-toolbar"
            style={{
              left: selectionToolbarPosition.left,
              top: selectionToolbarPosition.top,
            }}
            aria-label={t.selectedText}
          >
            <button type="button" onClick={() => void saveSelectedQuote()} disabled={busy}>
              {t.saveQuote}
            </button>
            <button type="button" onClick={sendSelectionToEvidenceCard} disabled={busy}>
              {t.makeEvidenceCard}
            </button>
          </div>
        )}

        <div className="reader-toolbar">
          <div>
            <span className="eyebrow">{t.chapter}</span>
            <h2>{activeChapter ? `${activeChapter.id}: ${activeChapter.title}` : t.noChapter}</h2>
          </div>
          <div className="state-actions">
            {stateOptions.map((stateName) => (
              <button
                key={stateName}
                onClick={() => void updateState(stateName)}
                disabled={!activeChapter || busy}
                type="button"
              >
                {t.stateLabels[stateName]}
              </button>
            ))}
          </div>
        </div>

        <article className="chapter-text" onMouseUp={handleTextSelection} onKeyUp={handleTextSelection}>
          {activeChapter ? activeChapter.text : t.emptyReader}
        </article>
      </section>

      <aside className="notes-pane">
        <header>
          <span className="eyebrow">{t.capture}</span>
          <h2>{t.buildUnderstanding}</h2>
        </header>

        <div className="capture-tabs" role="tablist" aria-label={t.captureType}>
          {[
            ["note", t.note],
            ["review", t.review],
            ["evidence", t.evidence],
          ].map(([id, label]) => (
            <button
              key={id}
              className={activeCapture === id ? "active" : ""}
              onClick={() => setActiveCapture(id as "note" | "review" | "evidence")}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>

        {activeCapture === "note" && (
          <form onSubmit={saveNote} className="capture-form">
            <label htmlFor="section">{t.section}</label>
            <select
              id="section"
              value={noteSection}
              onChange={(event) => setNoteSection(event.target.value)}
            >
              {noteSectionOptions.map((section) => (
                <option key={section} value={section}>
                  {t.noteSectionLabels[section]}
                </option>
              ))}
            </select>

            <label htmlFor="note">{t.note}</label>
            <textarea
              id="note"
              value={noteText}
              onChange={(event) => setNoteText(event.target.value)}
              placeholder={t.notePlaceholder}
            />

            <button type="submit" disabled={!activeChapter || busy || !noteText.trim()}>
              {t.saveNote}
            </button>
          </form>
        )}

        {activeCapture === "review" && (
          <form onSubmit={saveReviewCard} className="capture-form">
            <label htmlFor="review-question">{t.question}</label>
            <textarea
              id="review-question"
              className="compact"
              value={reviewQuestion}
              onChange={(event) => setReviewQuestion(event.target.value)}
              placeholder={t.reviewQuestionPlaceholder}
            />

            <label htmlFor="review-answer">{t.answer}</label>
            <textarea
              id="review-answer"
              value={reviewAnswer}
              onChange={(event) => setReviewAnswer(event.target.value)}
              placeholder={t.reviewAnswerPlaceholder}
            />

            <button
              type="submit"
              disabled={busy || !reviewQuestion.trim() || !reviewAnswer.trim()}
            >
              {t.saveReviewCard}
            </button>
          </form>
        )}

        {activeCapture === "evidence" && (
          <form onSubmit={saveEvidenceCard} className="capture-form">
            <label htmlFor="evidence-claim">{t.claim}</label>
            <textarea
              id="evidence-claim"
              className="compact"
              value={evidenceClaim}
              onChange={(event) => setEvidenceClaim(event.target.value)}
              placeholder={t.claimPlaceholder}
            />

            <label htmlFor="evidence-locator">{t.locator}</label>
            <input
              id="evidence-locator"
              value={evidenceLocator}
              onChange={(event) => setEvidenceLocator(event.target.value)}
              spellCheck={false}
            />

            <label htmlFor="evidence-support">{t.support}</label>
            <textarea
              id="evidence-support"
              value={evidenceSupport}
              onChange={(event) => setEvidenceSupport(event.target.value)}
              placeholder={t.supportPlaceholder}
            />

            <label htmlFor="evidence-confidence">{t.confidence}</label>
            <select
              id="evidence-confidence"
              value={evidenceConfidence}
              onChange={(event) => setEvidenceConfidence(event.target.value)}
            >
              {confidenceOptions.map((confidence) => (
                <option key={confidence} value={confidence}>
                  {t.confidenceLabels[confidence]}
                </option>
              ))}
            </select>

            <label htmlFor="evidence-not-explicit">{t.notExplicit}</label>
            <textarea
              id="evidence-not-explicit"
              className="compact"
              value={evidenceNotExplicit}
              onChange={(event) => setEvidenceNotExplicit(event.target.value)}
              placeholder={t.notExplicitPlaceholder}
            />

            <label htmlFor="evidence-inference">{t.myInference}</label>
            <textarea
              id="evidence-inference"
              className="compact"
              value={evidenceInference}
              onChange={(event) => setEvidenceInference(event.target.value)}
              placeholder={t.inferencePlaceholder}
            />

            <button
              type="submit"
              disabled={
                busy ||
                !evidenceClaim.trim() ||
                !evidenceLocator.trim() ||
                !evidenceSupport.trim()
              }
            >
              {t.saveEvidenceCard}
            </button>
          </form>
        )}

        <div className="message-stack" aria-live="polite">
          {busy && <p className="muted">{t.working}</p>}
          {message && <p className="success">{message}</p>}
          {error && <p className="error">{error}</p>}
        </div>
      </aside>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
