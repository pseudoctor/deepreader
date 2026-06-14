import React, { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { apiRequest, deleteWorkspace, importWorkspaceSource } from "./api";
import { formatChapterSynthesis, formatFeynmanFeedback } from "./formatters";
import {
  languages,
  selectionOutputLanguages,
  translations,
  type Language,
  type SelectionOutputLanguage,
} from "./i18n";
import {
  getInitialLanguage,
  getInitialObsidianFolder,
  getInitialReadingFontSize,
  getInitialSelectionOutputLanguage,
  getInitialWorkspaceLibrary,
} from "./storage";
import type {
  ActiveRecallResult,
  BookArgumentMapResult,
  Chapter,
  ChapterSynthesisResult,
  ChapterText,
  ConceptMapResult,
  EvidenceContextMatch,
  EvidenceContextResult,
  EvidenceTableResult,
  FeynmanCheckResult,
  LearningJournalFilter,
  LearningJournalItem,
  LearningJournalResult,
  LLMModelCatalog,
  LLMProviderList,
  LLMProviderStatus,
  LearningLoop,
  MainView,
  NextAction,
  ObsidianExportMode,
  ObsidianExportResult,
  OnePageBookAccountResult,
  ReadingFontSize,
  SelectionExplanationResult,
  SelectionReviewQuestionResult,
  SelectionToolbarPosition,
  Status,
  WorkspaceLibraryItem,
} from "./types";
import "./styles.css";

const defaultWorkspace = "workspaces/guns-germs-steel-reading";

const noteSectionOptions = [
  "Confusions",
  "Key Concepts",
  "My 3-5 Sentence Summary",
  "Applications",
] as const;

const noteTypeOptions = ["Quote", "My Thought", "AI Explanation", "Question"] as const;

const confidenceOptions = ["High", "Medium", "Low"] as const;

const stateOptions = ["reading", "done", "review", "weak"] as const;
const readingFontSizeOptions: { value: ReadingFontSize; label: string }[] = [
  { value: "small", label: "A-" },
  { value: "medium", label: "A" },
  { value: "large", label: "A+" },
];

const journalKindOptions = [
  "note",
  "quote",
  "question",
  "review_card",
  "evidence_card",
  "evidence_context",
  "weak_concept",
] as const;

const mapModeOptions = [
  "synthesis",
  "bookMap",
  "onePageAccount",
  "evidenceTable",
  "conceptMap",
  "learning",
] as const;

type MapMode = (typeof mapModeOptions)[number];

const sidebarWidthLimits = { min: 180, max: 360 };
const notesWidthLimits = { min: 220, max: 420 };
const readingGuideHeightLimits = { min: 84, max: 280 };

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function containsCjk(text: string): boolean {
  return /[\u4e00-\u9fff]/.test(text);
}

function resolveSelectionOutputLanguage(
  selected: SelectionOutputLanguage,
  uiLanguage: Language,
  selectedText: string,
): "zh" | "en" {
  if (selected === "zh" || selected === "en") return selected;
  return containsCjk(selectedText) || uiLanguage === "zh" ? "zh" : "en";
}

function resolveCurrentOutputLanguage(
  selected: SelectionOutputLanguage,
  uiLanguage: Language,
): "zh" | "en" {
  if (selected === "zh" || selected === "en") return selected;
  return uiLanguage === "zh" ? "zh" : "en";
}

function formatActionLabel(t: (typeof translations)[Language], action: NextAction): string {
  const key = `action_${action.kind}` as keyof typeof t;
  const label = t[key];
  return typeof label === "string" ? label : action.kind;
}

function workspacePathForFile(fileName: string): string {
  const stem = fileName.replace(/\.[^.]+$/, "") || "reading-workspace";
  const slug = stem
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `workspaces/${slug || "reading-workspace"}-reading`;
}

function App() {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const t = translations[language];
  const [workspace, setWorkspace] = useState(defaultWorkspace);
  const [status, setStatus] = useState<Status | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [activeChapter, setActiveChapter] = useState<ChapterText | null>(null);
  const [activeCapture, setActiveCapture] = useState<
    | "note"
    | "review"
    | "evidence"
    | "feynman"
    | "synthesis"
    | "bookMap"
    | "learning"
    | "context"
  >("note");
  const [mainView, setMainView] = useState<MainView>("reader");
  const [mapMode, setMapMode] = useState<MapMode>("synthesis");
  const [leftSidebarVisible, setLeftSidebarVisible] = useState(true);
  const [rightSidebarVisible, setRightSidebarVisible] = useState(true);
  const [readingGuideVisible, setReadingGuideVisible] = useState(true);
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(240);
  const [rightSidebarWidth, setRightSidebarWidth] = useState(280);
  const [readingGuideHeight, setReadingGuideHeight] = useState(154);
  const [readingFontSize, setReadingFontSize] =
    useState<ReadingFontSize>(getInitialReadingFontSize);
  const [noteSection, setNoteSection] = useState("Confusions");
  const [noteType, setNoteType] = useState("My Thought");
  const [noteText, setNoteText] = useState("");
  const [reviewQuestion, setReviewQuestion] = useState("");
  const [reviewAnswer, setReviewAnswer] = useState("");
  const [recallChapterId, setRecallChapterId] = useState("");
  const [activeRecallResult, setActiveRecallResult] = useState<ActiveRecallResult | null>(null);
  const [feynmanSummary, setFeynmanSummary] = useState("");
  const [feynmanResult, setFeynmanResult] = useState<FeynmanCheckResult | null>(null);
  const [synthesisStartChapterId, setSynthesisStartChapterId] = useState("");
  const [synthesisCount, setSynthesisCount] = useState(3);
  const [synthesisResult, setSynthesisResult] = useState<ChapterSynthesisResult | null>(null);
  const [bookArgumentMap, setBookArgumentMap] = useState<BookArgumentMapResult | null>(null);
  const [onePageBookAccount, setOnePageBookAccount] =
    useState<OnePageBookAccountResult | null>(null);
  const [evidenceTable, setEvidenceTable] = useState<EvidenceTableResult | null>(null);
  const [conceptMap, setConceptMap] = useState<ConceptMapResult | null>(null);
  const [evidenceClaim, setEvidenceClaim] = useState("");
  const [evidenceLocator, setEvidenceLocator] = useState("");
  const [evidenceSupport, setEvidenceSupport] = useState("");
  const [evidenceConfidence, setEvidenceConfidence] = useState("Medium");
  const [evidenceNotExplicit, setEvidenceNotExplicit] = useState("");
  const [evidenceInference, setEvidenceInference] = useState("");
  const [selectedText, setSelectedText] = useState("");
  const [selectionOutputLanguage, setSelectionOutputLanguage] =
    useState<SelectionOutputLanguage>(getInitialSelectionOutputLanguage);
  const [selectionToolbarPosition, setSelectionToolbarPosition] =
    useState<SelectionToolbarPosition | null>(null);
  const [obsidianFolder, setObsidianFolder] = useState(getInitialObsidianFolder);
  const [obsidianExportMode, setObsidianExportMode] =
    useState<ObsidianExportMode>("learning_archive");
  const [workspaceLibrary, setWorkspaceLibrary] =
    useState<WorkspaceLibraryItem[]>(getInitialWorkspaceLibrary);
  const [learningJournal, setLearningJournal] = useState<LearningJournalResult | null>(null);
  const [journalFilter, setJournalFilter] = useState<LearningJournalFilter>({
    kind: "all",
    chapter_id: "all",
  });
  const [selectedJournalItemId, setSelectedJournalItemId] = useState("");
  const [editingJournalItemId, setEditingJournalItemId] = useState("");
  const [journalEditText, setJournalEditText] = useState("");
  const [evidenceContextQuery, setEvidenceContextQuery] = useState("");
  const [evidenceContextResult, setEvidenceContextResult] =
    useState<EvidenceContextResult | null>(null);
  const [llmProviders, setLlmProviders] = useState<LLMProviderList | null>(null);
  const [providerDraft, setProviderDraft] = useState("");
  const [providerModelDraft, setProviderModelDraft] = useState("");
  const [providerBaseUrlDraft, setProviderBaseUrlDraft] = useState("");
  const [providerApiKeyDraft, setProviderApiKeyDraft] = useState("");
  const [providerModelCatalogs, setProviderModelCatalogs] = useState<
    Record<string, LLMModelCatalog>
  >({});
  const [loadingProviderModels, setLoadingProviderModels] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [weakConcept, setWeakConcept] = useState("");
  const [weakConceptNote, setWeakConceptNote] = useState("");
  const [weakConceptChapterId, setWeakConceptChapterId] = useState("");
  const [sourcePath, setSourcePath] = useState("");
  const [workspaceTarget, setWorkspaceTarget] = useState("");
  const [autoWorkspaceTarget, setAutoWorkspaceTarget] = useState("");
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [importPanelOpen, setImportPanelOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const chapterTextRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    window.localStorage.setItem("deep-reading-language", language);
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [language]);

  useEffect(() => {
    window.localStorage.setItem("deep-reading-obsidian-folder", obsidianFolder);
  }, [obsidianFolder]);

  useEffect(() => {
    window.localStorage.setItem("deep-reading-selection-output-language", selectionOutputLanguage);
  }, [selectionOutputLanguage]);

  useEffect(() => {
    window.localStorage.setItem("deep-reading-font-size", readingFontSize);
  }, [readingFontSize]);

  useEffect(() => {
    window.localStorage.setItem(
      "deep-reading-workspace-library",
      JSON.stringify(workspaceLibrary),
    );
    window.localStorage.setItem(
      "deep-reading-recent-workspaces",
      JSON.stringify(workspaceLibrary.map((item) => item.path).slice(0, 5)),
    );
  }, [workspaceLibrary]);

  useEffect(() => {
    void loadLLMProviders();
  }, []);

  const currentProvider = useMemo(() => {
    if (!llmProviders) return null;
    return (
      llmProviders.providers.find((provider) => provider.name === llmProviders.selected) ?? null
    );
  }, [llmProviders]);

  const providerModelCatalog = providerDraft ? providerModelCatalogs[providerDraft] : null;

  const filteredJournalItems = useMemo(() => {
    if (!learningJournal) return [];
    return learningJournal.items.filter((item) => {
      const kindMatches = journalFilter.kind === "all" || item.kind === journalFilter.kind;
      const chapterMatches =
        journalFilter.chapter_id === "all" || item.chapter_id === journalFilter.chapter_id;
      return kindMatches && chapterMatches;
    });
  }, [journalFilter, learningJournal]);

  const selectedJournalItem = useMemo<LearningJournalItem | null>(() => {
    return (
      filteredJournalItems.find((item) => item.id === selectedJournalItemId) ??
      filteredJournalItems[0] ??
      null
    );
  }, [filteredJournalItems, selectedJournalItemId]);

  function workspaceTitle(path: string): string {
    return path.split(/[\\/]/).filter(Boolean).at(-1) ?? path;
  }

  function rememberWorkspace(nextWorkspace: string, nextStatus: Status) {
    const item: WorkspaceLibraryItem = {
      path: nextWorkspace,
      title: workspaceTitle(nextWorkspace),
      last_opened_at: new Date().toISOString(),
      current: nextStatus.current,
      progress: nextStatus.progress,
      next_action: nextStatus.continue_reading.next_action,
      average_mastery: nextStatus.learning_loop.average_mastery,
      review_ready_count: nextStatus.learning_loop.review_ready.length,
      weak_count: nextStatus.learning_loop.weak_chapters.length,
    };
    setWorkspaceLibrary((current) => [
      item,
      ...current.filter((candidate) => candidate.path !== nextWorkspace),
    ].slice(0, 12));
  }

  function resetLoadedWorkspace(deletedWorkspace: string) {
    if (workspace !== deletedWorkspace) return;
    setStatus(null);
    setChapters([]);
    setActiveChapter(null);
    setLearningJournal(null);
    setSelectedJournalItemId("");
    setSynthesisResult(null);
    setBookArgumentMap(null);
    setOnePageBookAccount(null);
    setEvidenceTable(null);
    setConceptMap(null);
    setEvidenceContextResult(null);
  }

  function progressSummary(progress?: Record<string, number>): string {
    if (!progress) return t.noWorkspaceSummary;
    return Object.entries(progress)
      .map(([key, value]) => `${key}: ${value}`)
      .join(" · ");
  }

  function formatOpenedAt(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime()) || date.getTime() === 0) return t.notOpenedYet;
    return date.toLocaleDateString(language === "zh" ? "zh-CN" : "en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function chapterMasteryPercent(chapterId: string): number {
    return (
      status?.learning_loop.chapters.find((chapter) => chapter.id === chapterId)?.mastery_score ??
      0
    );
  }

  function journalKindLabel(kind: string): string {
    const labels: Record<string, string> = {
      note: t.note,
      quote: t.quote,
      question: t.question,
      review_card: t.review,
      evidence_card: t.evidence,
      evidence_context: t.evidenceContext,
      weak_concept: t.weakConcept,
    };
    return labels[kind] ?? kind;
  }

  function mapModeLabel(mode: MapMode): string {
    const labels: Record<MapMode, string> = {
      synthesis: t.synthesis,
      bookMap: t.bookMap,
      onePageAccount: t.onePageAccount,
      evidenceTable: t.evidenceTable,
      conceptMap: t.conceptMap,
      learning: t.learningLoop,
    };
    return labels[mode];
  }

  function journalSearchText(item: LearningJournalItem): string {
    if (item.target_text?.trim()) {
      return item.target_text.trim();
    }
    const withoutMarkdown = item.content
      .replace(/\*\*Locator\*\*[^\n]*/gi, "")
      .replace(/\*\*Source Locator\*\*[^\n]*/gi, "")
      .replace(/^#+\s*/gm, "")
      .replace(/^>\s?/gm, "")
      .trim();
    const lines = withoutMarkdown
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line) => !/^\*\*[^*]+\*\*/.test(line));
    return (lines.find((line) => line.length >= 8) ?? lines[0] ?? "").slice(0, 160);
  }

  function searchableTextWithOffsets(text: string): { normalized: string; offsets: number[] } {
    const offsets: number[] = [];
    let normalized = "";
    for (let index = 0; index < text.length; index += 1) {
      const char = text[index];
      if (/\s/.test(char)) continue;
      normalized += char.toLocaleLowerCase();
      offsets.push(index);
    }
    return { normalized, offsets };
  }

  function queryCandidates(query: string): string[] {
    const compact = query.replace(/\s+/g, " ").trim();
    const candidates = [compact, compact.slice(0, 180), compact.slice(0, 120), compact.slice(0, 80), compact.slice(0, 40)]
      .map((value) => value.trim())
      .filter((value) => value.length >= 4);
    return [...new Set(candidates)];
  }

  function scrollReaderToText(query: string) {
    const root = chapterTextRef.current;
    if (!root || !query.trim()) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    const candidates = queryCandidates(query);
    while (node) {
      const text = node.textContent ?? "";
      const searchableText = searchableTextWithOffsets(text);
      for (const candidate of candidates) {
        const searchableQuery = searchableTextWithOffsets(candidate).normalized;
        const index = searchableText.normalized.indexOf(searchableQuery);
        if (index >= 0 && searchableQuery.length > 0) {
          const start = searchableText.offsets[index];
          const end = (searchableText.offsets[index + searchableQuery.length - 1] ?? start) + 1;
          const range = document.createRange();
          range.setStart(node, start);
          range.setEnd(node, Math.min(end, text.length));
          const selection = window.getSelection();
          selection?.removeAllRanges();
          selection?.addRange(range);
          const rect = range.getBoundingClientRect();
          const rootRect = root.getBoundingClientRect();
          if (rect.height > 0) {
            root.scrollTo({
              top: root.scrollTop + rect.top - rootRect.top - root.clientHeight * 0.35,
              behavior: "smooth",
            });
          } else if (node.parentElement) {
            node.parentElement.scrollIntoView({ block: "center", behavior: "smooth" });
          }
          root.classList.add("reader-focus-highlight");
          window.setTimeout(() => {
            root.classList.remove("reader-focus-highlight");
          }, 2400);
          return;
        }
      }
      node = walker.nextNode();
    }
  }

  async function openJournalItemInReader(item: LearningJournalItem) {
    if (!item.chapter_id) return;
    setMainView("reader");
    await loadChapter(item.chapter_id);
    window.setTimeout(() => scrollReaderToText(journalSearchText(item)), 80);
  }

  function startEditingJournalItem(item: LearningJournalItem) {
    setEditingJournalItemId(item.id);
    setJournalEditText(item.content);
  }

  async function saveJournalItemEdit(item: LearningJournalItem) {
    if (!workspace) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiRequest<{ status: string }>(`/learning-journal/item`, {
        method: "PATCH",
        body: JSON.stringify({
          workspace,
          item_id: item.id,
          content: journalEditText,
        }),
      });
      setEditingJournalItemId("");
      await loadLearningJournal();
      setMessage(t.journalItemUpdated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedUpdateJournalItem);
    } finally {
      setBusy(false);
    }
  }

  async function deleteJournalItem(item: LearningJournalItem) {
    if (!workspace) return;
    if (!window.confirm(t.confirmDeleteJournalItem)) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiRequest<{ status: string }>(`/learning-journal/item`, {
        method: "DELETE",
        body: JSON.stringify({
          workspace,
          item_id: item.id,
        }),
      });
      setSelectedJournalItemId("");
      setEditingJournalItemId("");
      await loadLearningJournal();
      setMessage(t.journalItemDeleted);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedDeleteJournalItem);
    } finally {
      setBusy(false);
    }
  }

  function selectMainView(nextView: MainView) {
    setMainView(nextView);
    if (nextView === "journal") {
      void loadLearningJournal();
    }
  }

  function startHorizontalResize(side: "left" | "right", event: React.PointerEvent) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = side === "left" ? leftSidebarWidth : rightSidebarWidth;
    const limits = side === "left" ? sidebarWidthLimits : notesWidthLimits;

    function handleMove(moveEvent: PointerEvent) {
      const delta = moveEvent.clientX - startX;
      const nextWidth = side === "left" ? startWidth + delta : startWidth - delta;
      const clamped = clamp(nextWidth, limits.min, limits.max);
      if (side === "left") {
        setLeftSidebarWidth(clamped);
      } else {
        setRightSidebarWidth(clamped);
      }
    }

    function stopResize() {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", stopResize);
    }

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", stopResize);
  }

  function startVerticalResize(event: React.PointerEvent) {
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = readingGuideHeight;

    function handleMove(moveEvent: PointerEvent) {
      const delta = moveEvent.clientY - startY;
      setReadingGuideHeight(
        clamp(
          startHeight + delta,
          readingGuideHeightLimits.min,
          readingGuideHeightLimits.max,
        ),
      );
    }

    function stopResize() {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", stopResize);
    }

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", stopResize);
  }

  const readerGridColumns = [
    leftSidebarVisible ? `${leftSidebarWidth}px` : null,
    "minmax(0, 1fr)",
    rightSidebarVisible ? `${rightSidebarWidth}px` : null,
  ].filter(Boolean).join(" ");

  useEffect(() => {
    if (settingsOpen && providerDraft && !providerModelCatalogs[providerDraft]) {
      void loadLLMModels(providerDraft);
    }
  }, [settingsOpen, providerDraft, providerModelCatalogs]);

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
      const [nextStatus, chapterResult, journalResult] = await Promise.all([
        apiRequest<Status>(`/status?${query.toString()}`),
        apiRequest<{ chapters: Chapter[] }>(`/chapters?${query.toString()}`),
        apiRequest<LearningJournalResult>(`/learning-journal?${query.toString()}`),
      ]);
      setStatus(nextStatus);
      setChapters(chapterResult.chapters);
      setLearningJournal(journalResult);
      setSelectedJournalItemId(journalResult.items[0]?.id ?? "");
      if (chapterResult.chapters.length > 0) {
        setSynthesisStartChapterId(chapterResult.chapters[0].id);
        setRecallChapterId(chapterResult.chapters[0].id);
        setWeakConceptChapterId((current) => current || chapterResult.chapters[0].id);
        await loadChapter(chapterResult.chapters[0].id, nextWorkspace);
      }
      rememberWorkspace(nextWorkspace, nextStatus);
      setMessage(t.workspaceLoaded);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedLoadWorkspace);
    } finally {
      setBusy(false);
    }
  }

  async function loadLearningJournal(nextWorkspace = workspace) {
    if (!nextWorkspace.trim()) return;
    try {
      const query = new URLSearchParams({ workspace: nextWorkspace });
      const result = await apiRequest<LearningJournalResult>(`/learning-journal?${query.toString()}`);
      setLearningJournal(result);
      setSelectedJournalItemId((current) =>
        current && result.items.some((item) => item.id === current)
          ? current
          : result.items[0]?.id ?? "",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedLoadJournal);
    }
  }

  async function loadLLMProviders() {
    try {
      const result = await apiRequest<LLMProviderList>("/llm/providers");
      setLlmProviders(result);
      syncProviderDrafts(result, result.selected);
      void loadLLMModels(result.selected);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedLoadProviders);
    }
  }

  async function loadLLMModels(providerName = providerDraft) {
    if (!providerName) return;
    setLoadingProviderModels(true);
    try {
      const query = new URLSearchParams({ provider: providerName });
      const result = await apiRequest<LLMModelCatalog>(`/llm/models?${query.toString()}`);
      setProviderModelCatalogs((current) => ({ ...current, [providerName]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedLoadProviders);
    } finally {
      setLoadingProviderModels(false);
    }
  }

  function syncProviderDrafts(result: LLMProviderList, selectedName: string) {
    const provider = result.providers.find((item) => item.name === selectedName);
    setProviderDraft(selectedName);
    setProviderModelDraft(provider?.model ?? "");
    setProviderBaseUrlDraft(provider?.base_url ?? "");
    setProviderApiKeyDraft("");
  }

  function selectProviderDraft(nextProvider: string) {
    if (!llmProviders) return;
    syncProviderDrafts(llmProviders, nextProvider);
    void loadLLMModels(nextProvider);
  }

  async function saveLLMSettings(event: FormEvent) {
    event.preventDefault();
    if (!providerDraft) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await apiRequest<LLMProviderList>("/llm/settings", {
        method: "POST",
        body: JSON.stringify({
          provider: providerDraft,
          model: providerModelDraft,
          base_url: providerBaseUrlDraft,
          api_key: providerApiKeyDraft,
        }),
      });
      setLlmProviders(result);
      syncProviderDrafts(result, result.selected);
      setSettingsOpen(false);
      setMessage(t.providerSettingsSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedUpdateProvider);
    } finally {
      setBusy(false);
    }
  }

  async function addWeakConcept(event: FormEvent) {
    event.preventDefault();
    if (!weakConcept.trim() || !weakConceptChapterId) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiRequest("/weak-concepts", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: weakConceptChapterId,
          concept: weakConcept.trim(),
          note: weakConceptNote.trim(),
        }),
      });
      const query = new URLSearchParams({ workspace });
      const result = await apiRequest<LearningLoop>(`/learning-loop?${query.toString()}`);
      setStatus((current) => (current ? { ...current, learning_loop: result } : current));
      void loadLearningJournal();
      setWeakConcept("");
      setWeakConceptNote("");
      setMessage(t.weakConceptSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedAddWeakConcept);
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

  async function selectSourcePath() {
    if (!window.deepReadingDesktop) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const selectedSource = await window.deepReadingDesktop.selectSourcePath();
      if (!selectedSource) return;
      setSourcePath(selectedSource);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSelectSource);
    } finally {
      setBusy(false);
    }
  }

  async function selectWorkspaceTargetFolder() {
    if (!window.deepReadingDesktop) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const selectedTarget = await window.deepReadingDesktop.selectWorkspaceTargetFolder();
      if (!selectedTarget) return;
      setWorkspaceTarget(selectedTarget);
      setAutoWorkspaceTarget("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSelectWorkspaceTarget);
    } finally {
      setBusy(false);
    }
  }

  async function createWorkspace(event: FormEvent) {
    event.preventDefault();
    if (!window.deepReadingDesktop || !sourcePath.trim() || !workspaceTarget.trim()) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const createdWorkspace = await window.deepReadingDesktop.createWorkspaceFromSource(
        sourcePath.trim(),
        workspaceTarget.trim(),
      );
      setWorkspace(createdWorkspace);
      await loadWorkspace(createdWorkspace);
      setImportPanelOpen(false);
      setMessage(t.workspaceCreated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedCreateWorkspace);
    } finally {
      setBusy(false);
    }
  }

  async function importWorkspaceFromUpload(event: FormEvent) {
    event.preventDefault();
    if (!sourceFile) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await importWorkspaceSource(sourceFile, workspaceTarget);
      setWorkspace(result.workspace);
      await loadWorkspace(result.workspace);
      setSourceFile(null);
      setAutoWorkspaceTarget("");
      setImportPanelOpen(false);
      setMessage(t.workspaceCreated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedCreateWorkspace);
    } finally {
      setBusy(false);
    }
  }

  async function removeWorkspaceFromLibrary(workspacePath: string) {
    if (!window.confirm(t.confirmDeleteWorkspace)) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await deleteWorkspace(workspacePath);
      setWorkspaceLibrary((current) => current.filter((item) => item.path !== workspacePath));
      resetLoadedWorkspace(workspacePath);
      setMessage(t.workspaceDeleted);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedDeleteWorkspace);
    } finally {
      setBusy(false);
    }
  }

  function chooseUploadSource(file: File | null) {
    setSourceFile(file);
    if (!file) {
      setAutoWorkspaceTarget("");
    } else {
      const nextTarget = workspacePathForFile(file.name);
      if (!workspaceTarget.trim() || workspaceTarget === autoWorkspaceTarget) {
        setWorkspaceTarget(nextTarget);
        setAutoWorkspaceTarget(nextTarget);
      }
    }
    setError("");
    setMessage("");
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
      setWeakConceptChapterId(chapter.id);
      setFeynmanResult(null);
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
      top: Math.max(rect.top - 72, 12),
    });
  }

  async function saveSelectedQuote() {
    if (!activeChapter || !selectedText.trim()) return;
    const quoteText = selectedText.trim();
    setBusy(true);
    setError("");
    try {
      await apiRequest("/quotes", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: activeChapter.id,
          quote: quoteText,
          locator: `${activeChapter.id}: ${activeChapter.title}`,
        }),
      });
      setActiveCapture("note");
      setNoteType("Quote");
      setNoteSection("Key Concepts");
      setNoteText(quoteText);
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

  async function explainSelectedText() {
    if (!activeChapter || !selectedText.trim()) return;
    const text = selectedText.trim();
    const outputLanguage = resolveSelectionOutputLanguage(selectionOutputLanguage, language, text);
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<SelectionExplanationResult>("/selection-explanation", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: activeChapter.id,
          selected_text: text,
          language: outputLanguage,
        }),
      });
      setActiveCapture("note");
      setNoteType("AI Explanation");
      setNoteSection("Key Concepts");
      setNoteText(result.explanation);
      setMessage(t.explanationDrafted);
      setSelectedText("");
      setSelectionToolbarPosition(null);
      window.getSelection()?.removeAllRanges();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedExplainSelection);
    } finally {
      setBusy(false);
    }
  }

  async function makeReviewQuestionFromSelection() {
    if (!activeChapter || !selectedText.trim()) return;
    const text = selectedText.trim();
    const outputLanguage = resolveSelectionOutputLanguage(selectionOutputLanguage, language, text);
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<SelectionReviewQuestionResult>(
        "/selection-review-question",
        {
          method: "POST",
          body: JSON.stringify({
            workspace,
            chapter_id: activeChapter.id,
            selected_text: text,
            language: outputLanguage,
          }),
        },
      );
      setActiveCapture("review");
      setReviewQuestion(result.question);
      setReviewAnswer(result.answer);
      setMessage(t.reviewQuestionDrafted);
      setSelectedText("");
      setSelectionToolbarPosition(null);
      window.getSelection()?.removeAllRanges();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedMakeReviewQuestion);
    } finally {
      setBusy(false);
    }
  }

  function sendSelectionToFeynmanCheck() {
    if (!activeChapter || !selectedText.trim()) return;
    const text = selectedText.trim();
    setActiveCapture("feynman");
    setFeynmanSummary(`${t.selectedPassagePrompt}\n\n${text}\n\n${t.myExplanationPrompt}\n`);
    setSelectedText("");
    setSelectionToolbarPosition(null);
    window.getSelection()?.removeAllRanges();
  }

  function sendSelectionToConfusionNote() {
    if (!activeChapter || !selectedText.trim()) return;
    const text = selectedText.trim();
    setActiveCapture("note");
    setNoteType("Question");
    setNoteSection("Confusions");
    setNoteText(`${t.confusionDraftPrefix}\n\n> ${text.replace(/\n/g, "\n> ")}\n\n`);
    setSelectedText("");
    setSelectionToolbarPosition(null);
    window.getSelection()?.removeAllRanges();
  }

  async function runEvidenceContext(nextQuery = evidenceContextQuery) {
    if (!nextQuery.trim()) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await apiRequest<EvidenceContextResult>("/evidence-context", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: activeChapter?.id ?? null,
          query: nextQuery.trim(),
          limit: 6,
        }),
      });
      setEvidenceContextResult(result);
      setEvidenceContextQuery(result.query);
      setActiveCapture("context");
      setMessage(t.evidenceContextReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedBuildEvidenceContext);
    } finally {
      setBusy(false);
    }
  }

  async function sendSelectionToEvidenceContext() {
    if (!selectedText.trim()) return;
    const text = selectedText.trim();
    setEvidenceContextQuery(text);
    setSelectedText("");
    setSelectionToolbarPosition(null);
    window.getSelection()?.removeAllRanges();
    await runEvidenceContext(text);
  }

  function draftEvidenceFromContext(match: EvidenceContextMatch) {
    setActiveCapture("evidence");
    setEvidenceClaim(evidenceContextResult?.query ?? "");
    setEvidenceLocator(match.locator);
    setEvidenceSupport(match.snippet);
  }

  function draftNoteFromContext(match: EvidenceContextMatch) {
    setActiveCapture("note");
    setNoteType("AI Explanation");
    setNoteSection("Key Concepts");
    setNoteText(`${match.locator}\n\n${match.snippet}`);
  }

  async function saveEvidenceContext() {
    if (!evidenceContextResult) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/evidence-context/save", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          result: evidenceContextResult,
        }),
      });
      void loadLearningJournal();
      setMessage(t.evidenceContextSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveEvidenceContext);
    } finally {
      setBusy(false);
    }
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
          note_type: noteType,
          text: noteText.trim(),
        }),
      });
      void loadLearningJournal();
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
      void loadLearningJournal();
      setReviewQuestion("");
      setReviewAnswer("");
      setMessage(t.reviewCardSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveReviewCard);
    } finally {
      setBusy(false);
    }
  }

  async function generateActiveRecall() {
    if (!recallChapterId) return;
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<ActiveRecallResult>("/active-recall", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: recallChapterId,
          language: resolveCurrentOutputLanguage(selectionOutputLanguage, language),
        }),
      });
      setActiveRecallResult(result);
      setMessage(t.activeRecallReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedGenerateRecall);
    } finally {
      setBusy(false);
    }
  }

  async function saveActiveRecallCards() {
    if (!activeRecallResult) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/active-recall/save", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          result: activeRecallResult,
        }),
      });
      setMessage(t.activeRecallSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveRecall);
    } finally {
      setBusy(false);
    }
  }

  async function checkFeynmanSummary(event: FormEvent) {
    event.preventDefault();
    if (!activeChapter || !feynmanSummary.trim()) return;
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<FeynmanCheckResult>("/feynman-check", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: activeChapter.id,
          summary: feynmanSummary.trim(),
          language: resolveCurrentOutputLanguage(selectionOutputLanguage, language),
        }),
      });
      setFeynmanResult(result);
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedCheckSummary);
    } finally {
      setBusy(false);
    }
  }

  async function saveFeynmanFeedback() {
    if (!activeChapter || !feynmanResult) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/notes", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: activeChapter.id,
          section: "Coach Feedback",
          note_type: "AI Explanation",
          text: formatFeynmanFeedback(feynmanResult),
        }),
      });
      void loadLearningJournal();
      setMessage(t.feynmanFeedbackSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveFeynmanFeedback);
    } finally {
      setBusy(false);
    }
  }

  async function runChapterSynthesis(event: FormEvent) {
    event.preventDefault();
    if (!synthesisStartChapterId.trim()) return;
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<ChapterSynthesisResult>("/chapter-synthesis", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          start_chapter_id: synthesisStartChapterId,
          count: synthesisCount,
          language: resolveCurrentOutputLanguage(selectionOutputLanguage, language),
        }),
      });
      setSynthesisResult(result);
      setMessage(t.synthesisReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedRunSynthesis);
    } finally {
      setBusy(false);
    }
  }

  async function saveChapterSynthesis() {
    if (!synthesisResult) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/notes", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          chapter_id: synthesisResult.start_chapter_id,
          section: "Coach Feedback",
          note_type: "AI Explanation",
          text: formatChapterSynthesis(synthesisResult),
        }),
      });
      void loadLearningJournal();
      setMessage(t.synthesisSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveSynthesis);
    } finally {
      setBusy(false);
    }
  }

  async function buildBookMap() {
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<BookArgumentMapResult>("/book-argument-map", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          language: resolveCurrentOutputLanguage(selectionOutputLanguage, language),
        }),
      });
      setBookArgumentMap(result);
      setMessage(t.bookMapReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedBuildBookMap);
    } finally {
      setBusy(false);
    }
  }

  async function saveBookMap() {
    if (!bookArgumentMap) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/book-argument-map/save", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          result: bookArgumentMap,
        }),
      });
      setMessage(t.bookMapSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveBookMap);
    } finally {
      setBusy(false);
    }
  }

  async function buildOnePageBookAccount() {
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<OnePageBookAccountResult>("/one-page-book-account", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          language: resolveCurrentOutputLanguage(selectionOutputLanguage, language),
        }),
      });
      setOnePageBookAccount(result);
      setMessage(t.onePageAccountReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedBuildOnePageAccount);
    } finally {
      setBusy(false);
    }
  }

  async function saveOnePageBookAccount() {
    if (!onePageBookAccount) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/one-page-book-account/save", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          result: onePageBookAccount,
        }),
      });
      setMessage(t.onePageAccountSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveOnePageAccount);
    } finally {
      setBusy(false);
    }
  }

  async function buildEvidenceTable() {
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<EvidenceTableResult>("/evidence-table", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          language: resolveCurrentOutputLanguage(selectionOutputLanguage, language),
        }),
      });
      setEvidenceTable(result);
      setMessage(t.evidenceTableReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedBuildEvidenceTable);
    } finally {
      setBusy(false);
    }
  }

  async function saveEvidenceTable() {
    if (!evidenceTable) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/evidence-table/save", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          result: evidenceTable,
        }),
      });
      setMessage(t.evidenceTableSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveEvidenceTable);
    } finally {
      setBusy(false);
    }
  }

  async function buildConceptMap() {
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<ConceptMapResult>("/concept-map", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          language: resolveCurrentOutputLanguage(selectionOutputLanguage, language),
        }),
      });
      setConceptMap(result);
      setMessage(t.conceptMapReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedBuildConceptMap);
    } finally {
      setBusy(false);
    }
  }

  async function saveConceptMap() {
    if (!conceptMap) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/concept-map/save", {
        method: "POST",
        body: JSON.stringify({
          workspace,
          result: conceptMap,
        }),
      });
      setMessage(t.conceptMapSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failedSaveConceptMap);
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
      void loadLearningJournal();
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
          mode: obsidianExportMode,
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
    <main className="app-root">
      <header className="top-nav">
        <div className="top-nav-brand">
          <span className="brand-mark">DR</span>
          <div>
            <h1>{t.appTitle}</h1>
          </div>
        </div>
        <p className="top-nav-workspace" title={status?.workspace ?? workspace}>
          {status?.workspace ?? t.noWorkspaceLoaded}
        </p>
        <div className="main-view-switcher" role="tablist" aria-label={t.mainView}>
          {[
            ["reader", t.readerView],
            ["journal", t.journalView],
            ["map", t.mapView],
          ].map(([id, label]) => (
            <button
              key={id}
              className={mainView === id ? "active" : ""}
              onClick={() => selectMainView(id as MainView)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <div className="top-nav-actions">
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
          {currentProvider && (
            <p
              className={currentProvider.configured ? "provider-pill success" : "provider-pill muted"}
            >
              <strong>{currentProvider.display_name}</strong>
              <span>
                {currentProvider.configured ? t.providerConfigured : t.providerNotConfigured}
              </span>
            </p>
          )}
          <button type="button" onClick={() => setSettingsOpen(true)} disabled={!llmProviders}>
            {t.settings}
          </button>
        </div>
      </header>

      {mainView === "reader" && (
      <div className="workspace-layout" style={{ gridTemplateColumns: readerGridColumns }}>
        {leftSidebarVisible && (
        <aside className="sidebar">
        <form
          className="workspace-form"
          onSubmit={(event) => {
            event.preventDefault();
            void loadWorkspace();
          }}
        >
          <div className="sidebar-section-header">
            <label htmlFor="workspace">{t.workspace}</label>
            <button
              className="pane-toggle"
              type="button"
              onClick={() => setLeftSidebarVisible(false)}
              aria-label={t.hideLeftSidebar}
              title={t.hideLeftSidebar}
            >
              <span className="pane-icon pane-icon-left" aria-hidden="true" />
            </button>
          </div>
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

        <section className="import-workspace">
          <button
            className="import-workspace-toggle"
            type="button"
            onClick={() => setImportPanelOpen((current) => !current)}
          >
            {t.importBook}
          </button>
          {importPanelOpen && window.deepReadingDesktop && (
            <form className="create-workspace-form" onSubmit={createWorkspace}>
              <label htmlFor="source-path">{t.sourcePath}</label>
              <div className="path-picker-row">
                <input
                  id="source-path"
                  value={sourcePath}
                  onChange={(event) => setSourcePath(event.target.value)}
                  placeholder={t.sourcePathPlaceholder}
                  spellCheck={false}
                />
                <button type="button" onClick={() => void selectSourcePath()} disabled={busy}>
                  {t.selectSource}
                </button>
              </div>

              <label htmlFor="workspace-target">{t.workspaceTarget}</label>
              <div className="path-picker-row">
                <input
                  id="workspace-target"
                  value={workspaceTarget}
                  onChange={(event) => {
                    setWorkspaceTarget(event.target.value);
                    setAutoWorkspaceTarget("");
                  }}
                  placeholder={t.workspaceTargetPlaceholder}
                  spellCheck={false}
                />
                <button
                  type="button"
                  onClick={() => void selectWorkspaceTargetFolder()}
                  disabled={busy}
                >
                  {t.selectWorkspaceTarget}
                </button>
              </div>

              <button
                type="submit"
                disabled={busy || !sourcePath.trim() || !workspaceTarget.trim()}
              >
                {t.createWorkspace}
              </button>
            </form>
          )}
          {importPanelOpen && !window.deepReadingDesktop && (
            <form className="create-workspace-form" onSubmit={importWorkspaceFromUpload}>
              <label htmlFor="source-upload">{t.sourcePath}</label>
              <input
                id="source-upload"
                accept=".pdf,.epub,.docx,.txt,.text,.md,.markdown,.html,.htm,.rtf"
                type="file"
                onChange={(event) => chooseUploadSource(event.target.files?.[0] ?? null)}
              />
              <p className="muted">{t.supportedSourceFormats}</p>
              {sourceFile && (
                <p className="muted">
                  {t.selectedSource}: {sourceFile.name}
                </p>
              )}

              <label htmlFor="web-workspace-target">{t.workspaceTargetOptional}</label>
              <input
                id="web-workspace-target"
                value={workspaceTarget}
                onChange={(event) => {
                  setWorkspaceTarget(event.target.value);
                  setAutoWorkspaceTarget("");
                }}
                placeholder={t.webWorkspaceTargetPlaceholder}
                spellCheck={false}
              />

              <button type="submit" disabled={busy || !sourceFile}>
                {busy ? t.initializingBook : t.initializeBook}
              </button>
              <div className="message-stack" aria-live="polite">
                {message && <p className="success">{message}</p>}
                {error && <p className="error">{error}</p>}
              </div>
            </form>
          )}
        </section>

        <div className="recent-workspaces">
          <span className="eyebrow">{t.workspaceLibrary}</span>
          {workspaceLibrary.length === 0 ? (
            <p className="muted">{t.noRecentWorkspaces}</p>
          ) : (
            <div className="recent-workspace-list">
              {workspaceLibrary.map((item) => (
                <article className="recent-workspace-card" key={item.path} title={item.path}>
                  <button
                    className="recent-workspace-main"
                    onClick={() => {
                      setWorkspace(item.path);
                      void loadWorkspace(item.path);
                    }}
                    type="button"
                    disabled={busy}
                  >
                    <strong>{item.title ?? workspaceTitle(item.path)}</strong>
                    <span>{progressSummary(item.progress)}</span>
                    <span>
                      {t.lastOpened}: {formatOpenedAt(item.last_opened_at)}
                    </span>
                    {typeof item.average_mastery === "number" && (
                      <span>
                        {t.averageMastery} {item.average_mastery}% · {t.reviewReady}{" "}
                        {item.review_ready_count ?? 0} · {t.weakChapters} {item.weak_count ?? 0}
                      </span>
                    )}
                    {item.next_action && (
                      <em>{formatActionLabel(t, item.next_action)}</em>
                    )}
                  </button>
                  <button
                    className="workspace-delete-button"
                    type="button"
                    disabled={busy}
                    onClick={() => void removeWorkspaceFromLibrary(item.path)}
                    aria-label={`${t.deleteWorkspace}: ${item.title ?? workspaceTitle(item.path)}`}
                    title={t.deleteWorkspace}
                  >
                    ×
                  </button>
                </article>
              ))}
            </div>
          )}
        </div>

        <form className="export-form" onSubmit={exportToObsidian}>
          <span className="eyebrow">{t.export}</span>
          <label htmlFor="obsidian-export-mode">{t.obsidianExportMode}</label>
          <select
            id="obsidian-export-mode"
            value={obsidianExportMode}
            onChange={(event) => setObsidianExportMode(event.target.value as ObsidianExportMode)}
          >
            <option value="learning_archive">{t.obsidianLearningArchiveMode}</option>
            <option value="full">{t.obsidianFullMode}</option>
          </select>
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
          {chapters.map((chapter) => {
            const mastery = chapterMasteryPercent(chapter.id);
            return (
              <button
                key={chapter.id}
                className={activeChapter?.id === chapter.id ? "active" : ""}
                onClick={() => void loadChapter(chapter.id)}
                type="button"
              >
                <span>{chapter.id}</span>
                <strong>{chapter.title}</strong>
                <em>
                  {t.stateLabels[chapter.state as keyof typeof t.stateLabels] ?? chapter.state}
                </em>
                <i aria-label={`${t.masteryScore} ${mastery}%`}>
                  <b style={{ width: `${mastery}%` }} />
                </i>
              </button>
            );
          })}
        </nav>
        <div
          className="resize-handle resize-handle-left"
          role="separator"
          aria-label={t.resizeLeftSidebar}
          onPointerDown={(event) => startHorizontalResize("left", event)}
        />
        </aside>
        )}

        {!leftSidebarVisible && (
          <button
            className="pane-toggle pane-restore pane-restore-left"
            type="button"
            onClick={() => setLeftSidebarVisible(true)}
            aria-label={t.showLeftSidebar}
            title={t.showLeftSidebar}
          >
            <span className="pane-icon pane-icon-left" aria-hidden="true" />
          </button>
        )}

        <section
          className="reader-pane"
          style={{
            gridTemplateRows:
              activeChapter && readingGuideVisible
                ? `auto minmax(${readingGuideHeightLimits.min}px, ${readingGuideHeight}px) minmax(0, 1fr)`
                : "auto minmax(0, 1fr)",
          }}
        >
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
            <button type="button" onClick={() => void explainSelectedText()} disabled={busy}>
              {t.explainSelection}
            </button>
            <button
              type="button"
              onClick={() => void makeReviewQuestionFromSelection()}
              disabled={busy}
            >
              {t.makeReviewQuestion}
            </button>
            <button type="button" onClick={sendSelectionToFeynmanCheck} disabled={busy}>
              {t.feynman}
            </button>
            <button type="button" onClick={sendSelectionToConfusionNote} disabled={busy}>
              {t.confusion}
            </button>
            <button
              type="button"
              onClick={() => void sendSelectionToEvidenceContext()}
              disabled={busy}
            >
              {t.evidenceContext}
            </button>
          </div>
        )}

        <div className="reader-toolbar">
          <div>
            <span className="eyebrow">{t.chapter}</span>
            <h2>{activeChapter ? `${activeChapter.id}: ${activeChapter.title}` : t.noChapter}</h2>
          </div>
          <div className="state-actions">
            <div className="font-size-control" aria-label={t.readingFontSize}>
              {readingFontSizeOptions.map((option) => (
                <button
                  key={option.value}
                  className={readingFontSize === option.value ? "active" : ""}
                  type="button"
                  onClick={() => setReadingFontSize(option.value)}
                  title={t.readingFontSize}
                >
                  {option.label}
                </button>
              ))}
            </div>
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
            {activeChapter && (
              <button
                className="pane-toggle pane-toggle-toolbar"
                type="button"
                onClick={() => setReadingGuideVisible((current) => !current)}
                aria-label={readingGuideVisible ? t.hideReadingGuide : t.showReadingGuide}
                title={readingGuideVisible ? t.hideReadingGuide : t.showReadingGuide}
              >
                <span className="pane-icon pane-icon-top" aria-hidden="true" />
              </button>
            )}
          </div>
        </div>

        {activeChapter && readingGuideVisible && (
          <section
            className="reading-guide"
            aria-label={t.beforeReading}
            style={{ height: readingGuideHeight }}
          >
            <div className="reading-guide-header">
              <span className="eyebrow">{t.beforeReading}</span>
            </div>
            <div className="reading-guide-grid">
              <article>
                <h3>{t.coreQuestion}</h3>
                <p>{activeChapter.reading_guide.core_question}</p>
              </article>
              <article>
                <h3>{t.evidenceToSeek}</h3>
                <p>{activeChapter.reading_guide.evidence_to_seek}</p>
              </article>
              <article>
                <h3>{t.afterReadingRecall}</h3>
                <p>{activeChapter.reading_guide.recall_prompt}</p>
              </article>
            </div>
            <div
              className="resize-handle resize-handle-guide"
              role="separator"
              aria-label={t.resizeReadingGuide}
              onPointerDown={startVerticalResize}
            />
          </section>
        )}

        <article
          ref={chapterTextRef}
          className={`chapter-text chapter-text-${readingFontSize}`}
          onMouseUp={handleTextSelection}
          onKeyUp={handleTextSelection}
        >
          {activeChapter ? activeChapter.text : t.emptyReader}
        </article>
        </section>

        {!rightSidebarVisible && (
          <button
            className="pane-toggle pane-restore pane-restore-right"
            type="button"
            onClick={() => setRightSidebarVisible(true)}
            aria-label={t.showRightSidebar}
            title={t.showRightSidebar}
          >
            <span className="pane-icon pane-icon-right" aria-hidden="true" />
          </button>
        )}

        {rightSidebarVisible && (
        <aside className="notes-pane">
        <div
          className="resize-handle resize-handle-right"
          role="separator"
          aria-label={t.resizeRightSidebar}
          onPointerDown={(event) => startHorizontalResize("right", event)}
        />
        <button
          className="pane-toggle pane-toggle-inline pane-toggle-right"
          type="button"
          onClick={() => setRightSidebarVisible(false)}
          aria-label={t.hideRightSidebar}
          title={t.hideRightSidebar}
        >
          <span className="pane-icon pane-icon-right" aria-hidden="true" />
        </button>
        <header>
          <span className="eyebrow">{t.capture}</span>
          <h2>{t.buildUnderstanding}</h2>
        </header>

        <div className="capture-tabs" role="tablist" aria-label={t.captureType}>
          {[
            ["note", t.note],
            ["review", t.review],
            ["evidence", t.evidence],
            ["feynman", t.feynman],
            ["context", t.evidenceContext],
          ].map(([id, label]) => (
            <button
              key={id}
              className={activeCapture === id ? "active" : ""}
              onClick={() =>
                setActiveCapture(
                  id as "note" | "review" | "evidence" | "feynman" | "context",
                )
              }
              type="button"
            >
              {label}
            </button>
          ))}
        </div>

        <div className="selection-output-control">
          <label htmlFor="selection-output-language">{t.selectionOutputLanguage}</label>
          <select
            id="selection-output-language"
            value={selectionOutputLanguage}
            onChange={(event) =>
              setSelectionOutputLanguage(event.target.value as SelectionOutputLanguage)
            }
          >
            {selectionOutputLanguages.map((option) => {
              const label = t[option.labelKey as keyof typeof t];
              return (
                <option key={option.code} value={option.code}>
                  {typeof label === "string" ? label : option.code}
                </option>
              );
            })}
          </select>
        </div>

        {activeCapture === "note" && (
          <form onSubmit={saveNote} className="capture-form">
            <label htmlFor="note-type">{t.noteType}</label>
            <select
              id="note-type"
              value={noteType}
              onChange={(event) => setNoteType(event.target.value)}
            >
              {noteTypeOptions.map((type) => (
                <option key={type} value={type}>
                  {t.noteTypeLabels[type]}
                </option>
              ))}
            </select>

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

            <div className="panel-divider" />

            <span className="eyebrow">{t.activeRecall}</span>
            <label htmlFor="recall-chapter">{t.recallChapter}</label>
            <select
              id="recall-chapter"
              value={recallChapterId}
              onChange={(event) => {
                setRecallChapterId(event.target.value);
                setActiveRecallResult(null);
              }}
            >
              {chapters.map((chapter) => (
                <option key={chapter.id} value={chapter.id}>
                  {chapter.id}: {chapter.title}
                </option>
              ))}
            </select>

            <button type="button" onClick={() => void generateActiveRecall()} disabled={busy}>
              {t.generateRecall}
            </button>

            {activeRecallResult && (
              <section className="feynman-result">
                {!activeRecallResult.eligible_for_review && (
                  <p className="muted">{t.recallNotCompleted}</p>
                )}

                {activeRecallResult.questions.map((item) => (
                  <article key={item.question} className="recall-item">
                    <h3>{item.question}</h3>
                    <p>
                      <strong>{t.answerHint}</strong> {item.answer_hint}
                    </p>
                  </article>
                ))}

                <button
                  type="button"
                  onClick={() => void saveActiveRecallCards()}
                  disabled={busy}
                >
                  {t.saveAllRecallCards}
                </button>
              </section>
            )}
          </form>
        )}

        {activeCapture === "feynman" && (
          <form onSubmit={checkFeynmanSummary} className="capture-form">
            <label htmlFor="feynman-summary">{t.feynmanSummary}</label>
            <textarea
              id="feynman-summary"
              value={feynmanSummary}
              onChange={(event) => setFeynmanSummary(event.target.value)}
              placeholder={t.feynmanSummaryPlaceholder}
            />

            <button type="submit" disabled={!activeChapter || busy || !feynmanSummary.trim()}>
              {t.checkSummary}
            </button>

            {feynmanResult && (
              <section className="feynman-result">
                <h3>{t.accuratePoints}</h3>
                <ul>
                  {(feynmanResult.accurate_points.length > 0
                    ? feynmanResult.accurate_points
                    : [t.noFeedbackItems]
                  ).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.vaguePoints}</h3>
                <ul>
                  {(feynmanResult.vague_points.length > 0
                    ? feynmanResult.vague_points
                    : [t.noFeedbackItems]
                  ).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.missingCausalLinks}</h3>
                <ul>
                  {(feynmanResult.missing_causal_links.length > 0
                    ? feynmanResult.missing_causal_links
                    : [t.noFeedbackItems]
                  ).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.unsupportedLeaps}</h3>
                <ul>
                  {(feynmanResult.unsupported_leaps.length > 0
                    ? feynmanResult.unsupported_leaps
                    : [t.noFeedbackItems]
                  ).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.rewrittenVersion}</h3>
                <p>{feynmanResult.rewritten_version}</p>

                <button type="button" onClick={() => void saveFeynmanFeedback()} disabled={busy}>
                  {t.saveFeynmanFeedback}
                </button>
              </section>
            )}
          </form>
        )}

        {activeCapture === "synthesis" && (
          <form onSubmit={runChapterSynthesis} className="capture-form">
            <label htmlFor="synthesis-start">{t.synthesisStart}</label>
            <select
              id="synthesis-start"
              value={synthesisStartChapterId}
              onChange={(event) => setSynthesisStartChapterId(event.target.value)}
            >
              {chapters.map((chapter) => (
                <option key={chapter.id} value={chapter.id}>
                  {chapter.id}: {chapter.title}
                </option>
              ))}
            </select>

            <label htmlFor="synthesis-count">{t.synthesisCount}</label>
            <input
              id="synthesis-count"
              min={1}
              max={10}
              type="number"
              value={synthesisCount}
              onChange={(event) => setSynthesisCount(Number(event.target.value))}
            />

            <button type="submit" disabled={busy || !synthesisStartChapterId}>
              {t.runSynthesis}
            </button>

            {synthesisResult && (
              <section className="feynman-result">
                <h3>{t.commonQuestion}</h3>
                <p>{synthesisResult.common_question}</p>

                <h3>{t.recurringConcepts}</h3>
                <ul>
                  {synthesisResult.recurring_concepts.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.argumentProgression}</h3>
                <p>{synthesisResult.argument_progression}</p>

                <h3>{t.openQuestions}</h3>
                <ul>
                  {synthesisResult.open_questions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <button type="button" onClick={() => void saveChapterSynthesis()} disabled={busy}>
                  {t.saveSynthesisFeedback}
                </button>
              </section>
            )}
          </form>
        )}

        {activeCapture === "context" && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void runEvidenceContext();
            }}
            className="capture-form"
          >
            <label htmlFor="evidence-context-query">{t.evidenceContextQuery}</label>
            <textarea
              id="evidence-context-query"
              className="compact"
              value={evidenceContextQuery}
              onChange={(event) => setEvidenceContextQuery(event.target.value)}
              placeholder={t.evidenceContextPlaceholder}
            />

            <button type="submit" disabled={busy || !evidenceContextQuery.trim()}>
              {t.findEvidenceContext}
            </button>

            {evidenceContextResult && (
              <section className="feynman-result evidence-context-results">
                <h3>{t.evidenceContextResults}</h3>
                {evidenceContextResult.matches.length === 0 ? (
                  <p className="muted">{t.noEvidenceContextMatches}</p>
                ) : (
                  evidenceContextResult.matches.map((match) => (
                    <article
                      key={`${match.source_type}-${match.locator}-${match.snippet}`}
                      className="context-match"
                    >
                      <h3>{match.locator}</h3>
                      <p>
                        <strong>{t.sourceType}</strong> {match.source_type} ·{" "}
                        <strong>{t.score}</strong> {match.score}
                      </p>
                      <p>{match.snippet}</p>
                      <div className="context-match-actions">
                        <button
                          type="button"
                          onClick={() => draftEvidenceFromContext(match)}
                          disabled={busy}
                        >
                          {t.draftEvidenceCard}
                        </button>
                        <button
                          type="button"
                          onClick={() => draftNoteFromContext(match)}
                          disabled={busy}
                        >
                          {t.copyToNoteDraft}
                        </button>
                      </div>
                    </article>
                  ))
                )}
                <button
                  type="button"
                  onClick={() => void saveEvidenceContext()}
                  disabled={busy}
                >
                  {t.saveEvidenceContext}
                </button>
              </section>
            )}
          </form>
        )}

        {activeCapture === "bookMap" && (
          <div className="capture-form">
            <button type="button" onClick={() => void buildBookMap()} disabled={busy}>
              {t.buildBookMap}
            </button>
            <button
              type="button"
              onClick={() => void buildOnePageBookAccount()}
              disabled={busy}
            >
              {t.buildOnePageAccount}
            </button>
            <button type="button" onClick={() => void buildEvidenceTable()} disabled={busy}>
              {t.buildEvidenceTable}
            </button>
            <button type="button" onClick={() => void buildConceptMap()} disabled={busy}>
              {t.buildConceptMap}
            </button>

            {bookArgumentMap && (
              <section className="feynman-result">
                <h3>{t.coreProblem}</h3>
                <p>{bookArgumentMap.core_problem}</p>

                <h3>{t.coreAnswer}</h3>
                <p>{bookArgumentMap.core_answer}</p>

                <h3>{t.argumentChain}</h3>
                <ul>
                  {bookArgumentMap.argument_chain.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.keyEvidence}</h3>
                <ul>
                  {bookArgumentMap.key_evidence.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.rebuttalsAndLimits}</h3>
                <ul>
                  {bookArgumentMap.rebuttals_and_limits.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <button type="button" onClick={() => void saveBookMap()} disabled={busy}>
                  {t.saveBookMap}
                </button>
              </section>
            )}

            {evidenceTable && (
              <section className="feynman-result">
                <h3>{t.evidenceTable}</h3>
                <p>
                  {evidenceTable.card_count} {t.evidence}
                </p>

                {evidenceTable.cards.map((card) => (
                  <article key={`${card.claim}-${card.source_locator}`} className="recall-item">
                    <h3>{card.claim || t.claim}</h3>
                    <p>
                      <strong>{t.sourceLocator}</strong> {card.source_locator || "TBD"}
                    </p>
                    <p>
                      <strong>{t.support}</strong> {card.support || "TBD"}
                    </p>
                    <p>
                      <strong>{t.confidence}</strong> {card.confidence || "TBD"}
                    </p>
                    <p>
                      <strong>{t.notExplicitShort}</strong> {card.not_explicit || "TBD"}
                    </p>
                    <p>
                      <strong>{t.inference}</strong> {card.inference || "TBD"}
                    </p>
                  </article>
                ))}

                <button type="button" onClick={() => void saveEvidenceTable()} disabled={busy}>
                  {t.saveEvidenceTable}
                </button>
              </section>
            )}

            {conceptMap && (
              <section className="feynman-result">
                <h3>{t.conceptMap}</h3>
                <p>
                  {conceptMap.node_count} {t.nodes} · {conceptMap.link_count} {t.links}
                </p>

                <h3>{t.nodes}</h3>
                <ul>
                  {conceptMap.nodes.map((node) => (
                    <li key={node.id}>
                      {node.label} ({node.type}, {node.mastery_score}%)
                    </li>
                  ))}
                </ul>

                <h3>{t.links}</h3>
                <ul>
                  {conceptMap.links.map((link) => (
                    <li key={`${link.source}-${link.relation}-${link.target}`}>
                      {link.source} - {link.relation} - {link.target}: {link.evidence}
                    </li>
                  ))}
                </ul>

                <button type="button" onClick={() => void saveConceptMap()} disabled={busy}>
                  {t.saveConceptMap}
                </button>
              </section>
            )}

            {onePageBookAccount && (
              <section className="feynman-result">
                <h3>{t.onePageAccount}</h3>
                <p>
                  {onePageBookAccount.title} · {onePageBookAccount.completed_count}/
                  {onePageBookAccount.chapter_count} · {onePageBookAccount.average_mastery}%
                </p>

                <h3>{t.coreAnswer}</h3>
                <p>{onePageBookAccount.core_account}</p>

                <h3>{t.argumentChain}</h3>
                <ul>
                  {onePageBookAccount.core_argument_chain.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.strongestEvidence}</h3>
                <ul>
                  {onePageBookAccount.strongest_evidence.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.weakPoints}</h3>
                <ul>
                  {onePageBookAccount.weak_points.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h3>{t.applicationPrompts}</h3>
                <ul>
                  {onePageBookAccount.application_prompts.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <button
                  type="button"
                  onClick={() => void saveOnePageBookAccount()}
                  disabled={busy}
                >
                  {t.saveOnePageAccount}
                </button>
              </section>
            )}
          </div>
        )}

        {activeCapture === "learning" && (
          <div className="capture-form">
            {status ? (
              <section className="learning-loop learning-panel">
                <span className="eyebrow">{t.learningLoop}</span>
                <div className="learning-loop-metrics">
                  <p>
                    <strong>{status.learning_loop.average_mastery}%</strong>
                    <span>{t.averageMastery}</span>
                  </p>
                  <p>
                    <strong>{status.learning_loop.completed_count}</strong>
                    <span>{t.completedChapters}</span>
                  </p>
                  <p>
                    <strong>{status.learning_loop.review_ready.length}</strong>
                    <span>{t.reviewReady}</span>
                  </p>
                  <p>
                    <strong>{status.learning_loop.weak_chapters.length}</strong>
                    <span>{t.weakChapters}</span>
                  </p>
                </div>
                <div className="mastery-meter" aria-label={`${t.averageMastery} ${status.learning_loop.average_mastery}%`}>
                  <span style={{ width: `${status.learning_loop.average_mastery}%` }} />
                </div>
                <button
                  className="learning-next-action"
                  type="button"
                  disabled={busy || !status.continue_reading.next_action.chapter_id}
                  onClick={() => {
                    const chapterId = status.continue_reading.next_action.chapter_id;
                    if (chapterId) void loadChapter(chapterId);
                  }}
                >
                  <span>{t.nextStep}</span>
                  <strong>{formatActionLabel(t, status.continue_reading.next_action)}</strong>
                  {status.continue_reading.next_action.chapter_id && (
                    <em>
                      {status.continue_reading.next_action.chapter_id}:{" "}
                      {status.continue_reading.next_action.title}
                    </em>
                  )}
                </button>
                {status.learning_loop.synthesis_due && (
                  <p className="success">{t.synthesisDue}</p>
                )}
                <div className="chapter-mastery-list">
                  <strong>{t.chapterMastery}</strong>
                  {status.learning_loop.chapters.slice(0, 6).map((chapter) => (
                    <button
                      key={chapter.id}
                      type="button"
                      onClick={() => void loadChapter(chapter.id)}
                      disabled={busy}
                    >
                      <span>
                        {chapter.id}: {chapter.title}
                      </span>
                      <em>{chapter.mastery_score}%</em>
                      <i>
                        <b style={{ width: `${chapter.mastery_score}%` }} />
                      </i>
                    </button>
                  ))}
                </div>
                <div className="weak-chapter-list">
                  <strong>{t.weakChapters}</strong>
                  {status.learning_loop.weak_chapters.length === 0 ? (
                    <span className="muted">{t.noWeakChapters}</span>
                  ) : (
                    status.learning_loop.weak_chapters.slice(0, 4).map((chapter) => (
                      <button
                        key={chapter.id}
                        type="button"
                        onClick={() => void loadChapter(chapter.id)}
                        disabled={busy}
                        title={chapter.weak_reasons.join(" · ")}
                      >
                        <span>
                          {chapter.id}: {chapter.title}
                        </span>
                        <em>
                          {t.masteryScore} {chapter.mastery_score}%
                        </em>
                      </button>
                    ))
                  )}
                </div>

                <div className="weak-concept-list">
                  <strong>{t.weakConcepts}</strong>
                  {status.learning_loop.weak_concepts.length === 0 ? (
                    <span className="muted">{t.noWeakConcepts}</span>
                  ) : (
                    status.learning_loop.weak_concepts.slice(0, 4).map((item) => (
                      <button
                        key={`${item.chapter_id}-${item.concept}`}
                        type="button"
                        onClick={() => void loadChapter(item.chapter_id)}
                        disabled={busy}
                        title={item.note}
                      >
                        <span>{item.concept}</span>
                        <em>
                          {item.chapter_id}: {item.title}
                        </em>
                      </button>
                    ))
                  )}
                </div>

                <form className="weak-concept-form" onSubmit={addWeakConcept}>
                  <label htmlFor="weak-concept">{t.weakConcept}</label>
                  <input
                    id="weak-concept"
                    value={weakConcept}
                    onChange={(event) => setWeakConcept(event.target.value)}
                    placeholder={t.weakConceptPlaceholder}
                  />
                  <label htmlFor="weak-concept-chapter">{t.chapter}</label>
                  <select
                    id="weak-concept-chapter"
                    value={weakConceptChapterId}
                    onChange={(event) => setWeakConceptChapterId(event.target.value)}
                  >
                    {chapters.map((chapter) => (
                      <option key={chapter.id} value={chapter.id}>
                        {chapter.id}: {chapter.title}
                      </option>
                    ))}
                  </select>
                  <label htmlFor="weak-concept-note">{t.weakConceptNote}</label>
                  <textarea
                    id="weak-concept-note"
                    className="mini"
                    value={weakConceptNote}
                    onChange={(event) => setWeakConceptNote(event.target.value)}
                    placeholder={t.weakConceptNotePlaceholder}
                  />
                  <button
                    type="submit"
                    disabled={busy || !weakConcept.trim() || !weakConceptChapterId}
                  >
                    {t.addWeakConcept}
                  </button>
                </form>
              </section>
            ) : (
              <p className="muted">{t.noWorkspaceLoaded}</p>
            )}
          </div>
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
      )}
      </div>
      )}

      {mainView === "journal" && (
        <div className="journal-layout">
          <aside className="journal-filters">
            <header>
              <span className="eyebrow">{t.journalView}</span>
              <h2>{t.learningJournal}</h2>
            </header>
            <label htmlFor="journal-kind">{t.captureType}</label>
            <select
              id="journal-kind"
              value={journalFilter.kind}
              onChange={(event) =>
                setJournalFilter((current) => ({ ...current, kind: event.target.value }))
              }
            >
              <option value="all">{t.allTypes}</option>
              {journalKindOptions.map((kind) => (
                <option key={kind} value={kind}>
                  {journalKindLabel(kind)}
                  {learningJournal?.groups[kind] ? ` (${learningJournal.groups[kind]})` : ""}
                </option>
              ))}
            </select>

            <label htmlFor="journal-chapter">{t.chapter}</label>
            <select
              id="journal-chapter"
              value={journalFilter.chapter_id}
              onChange={(event) =>
                setJournalFilter((current) => ({
                  ...current,
                  chapter_id: event.target.value,
                }))
              }
            >
              <option value="all">{t.allChapters}</option>
              {chapters.map((chapter) => (
                <option key={chapter.id} value={chapter.id}>
                  {chapter.id}: {chapter.title}
                </option>
              ))}
            </select>

            <button type="button" onClick={() => void loadLearningJournal()} disabled={busy}>
              {t.refresh}
            </button>
          </aside>

          <section className="journal-stream">
            <header>
              <div>
                <span className="eyebrow">{t.learningJournal}</span>
                <h2>{filteredJournalItems.length} {t.journalItems}</h2>
              </div>
            </header>
            {filteredJournalItems.length === 0 ? (
              <p className="muted">{t.journalEmpty}</p>
            ) : (
              filteredJournalItems.map((item) => (
                <button
                  key={item.id}
                  className={selectedJournalItem?.id === item.id ? "journal-item active" : "journal-item"}
                  type="button"
                  onClick={() => {
                    setSelectedJournalItemId(item.id);
                    setEditingJournalItemId("");
                  }}
                >
                  <span>{journalKindLabel(item.kind)}</span>
                  <strong>{item.title}</strong>
                  <em>{item.locator}</em>
                  <p>{item.content}</p>
                </button>
              ))
            )}
          </section>

          <aside className="journal-detail">
            <header>
              <span className="eyebrow">{t.journalDetail}</span>
              <h2>{selectedJournalItem?.title ?? t.noSelection}</h2>
            </header>
            {selectedJournalItem ? (
              <>
                <dl>
                  <div>
                    <dt>{t.captureType}</dt>
                    <dd>{journalKindLabel(selectedJournalItem.kind)}</dd>
                  </div>
                  <div>
                    <dt>{t.locator}</dt>
                    <dd>{selectedJournalItem.locator}</dd>
                  </div>
                  <div>
                    <dt>{t.sourcePathLabel}</dt>
                    <dd>{selectedJournalItem.source_path}</dd>
                  </div>
                </dl>
                {editingJournalItemId === selectedJournalItem.id ? (
                  <div className="journal-edit-form">
                    <textarea
                      value={journalEditText}
                      onChange={(event) => setJournalEditText(event.target.value)}
                    />
                    <div className="inline-actions">
                      <button
                        type="button"
                        onClick={() => void saveJournalItemEdit(selectedJournalItem)}
                        disabled={busy}
                      >
                        {t.saveChanges}
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => setEditingJournalItemId("")}
                        disabled={busy}
                      >
                        {t.cancel}
                      </button>
                    </div>
                  </div>
                ) : (
                  <article className="journal-detail-content">
                    {selectedJournalItem.content}
                  </article>
                )}
                <div className="inline-actions">
                  {selectedJournalItem.chapter_id && (
                    <button
                      type="button"
                      onClick={() => void openJournalItemInReader(selectedJournalItem)}
                      disabled={busy}
                    >
                      {t.openInReader}
                    </button>
                  )}
                  {selectedJournalItem.editable && editingJournalItemId !== selectedJournalItem.id && (
                    <>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => startEditingJournalItem(selectedJournalItem)}
                        disabled={busy}
                      >
                        {t.edit}
                      </button>
                      <button
                        type="button"
                        className="danger-button"
                        onClick={() => void deleteJournalItem(selectedJournalItem)}
                        disabled={busy}
                      >
                        {t.delete}
                      </button>
                    </>
                  )}
                </div>
              </>
            ) : (
              <p className="muted">{t.journalEmpty}</p>
            )}
            <div className="message-stack" aria-live="polite">
              {busy && <p className="muted">{t.working}</p>}
              {message && <p className="success">{message}</p>}
              {error && <p className="error">{error}</p>}
            </div>
          </aside>
        </div>
      )}

      {mainView === "map" && (
        <div className="map-layout">
          <aside className="map-sidebar">
            <header>
              <span className="eyebrow">{t.mapView}</span>
              <h2>{t.bookMap}</h2>
            </header>
            <nav className="map-mode-list" aria-label={t.mapView}>
              {mapModeOptions.map((mode) => (
                <button
                  key={mode}
                  className={mapMode === mode ? "active" : ""}
                  type="button"
                  onClick={() => setMapMode(mode)}
                >
                  {mapModeLabel(mode)}
                </button>
              ))}
            </nav>
          </aside>

          <section className="map-stage">
            <header>
              <div>
                <span className="eyebrow">{t.mapOutput}</span>
                <h2>{mapModeLabel(mapMode)}</h2>
              </div>
            </header>

            {mapMode === "synthesis" && (
              <form onSubmit={runChapterSynthesis} className="capture-form map-tool">
                <label htmlFor="map-synthesis-start">{t.synthesisStart}</label>
                <select
                  id="map-synthesis-start"
                  value={synthesisStartChapterId}
                  onChange={(event) => setSynthesisStartChapterId(event.target.value)}
                >
                  {chapters.map((chapter) => (
                    <option key={chapter.id} value={chapter.id}>
                      {chapter.id}: {chapter.title}
                    </option>
                  ))}
                </select>
                <label htmlFor="map-synthesis-count">{t.synthesisCount}</label>
                <input
                  id="map-synthesis-count"
                  min={1}
                  max={10}
                  type="number"
                  value={synthesisCount}
                  onChange={(event) => setSynthesisCount(Number(event.target.value))}
                />
                <button type="submit" disabled={busy || !synthesisStartChapterId}>
                  {t.runSynthesis}
                </button>
                {synthesisResult ? (
                  <section className="feynman-result">
                    <h3>{t.commonQuestion}</h3>
                    <p>{synthesisResult.common_question}</p>
                    <h3>{t.recurringConcepts}</h3>
                    <ul>{synthesisResult.recurring_concepts.map((item) => <li key={item}>{item}</li>)}</ul>
                    <h3>{t.argumentProgression}</h3>
                    <p>{synthesisResult.argument_progression}</p>
                    <h3>{t.openQuestions}</h3>
                    <ul>{synthesisResult.open_questions.map((item) => <li key={item}>{item}</li>)}</ul>
                    <button type="button" onClick={() => void saveChapterSynthesis()} disabled={busy}>
                      {t.saveSynthesisFeedback}
                    </button>
                  </section>
                ) : (
                  <p className="muted">{t.noMapResult}</p>
                )}
              </form>
            )}

            {mapMode === "bookMap" && (
              <div className="capture-form map-tool">
                <button type="button" onClick={() => void buildBookMap()} disabled={busy}>
                  {t.buildBookMap}
                </button>
                {bookArgumentMap ? (
                  <section className="feynman-result">
                    <h3>{t.coreProblem}</h3>
                    <p>{bookArgumentMap.core_problem}</p>
                    <h3>{t.coreAnswer}</h3>
                    <p>{bookArgumentMap.core_answer}</p>
                    <h3>{t.argumentChain}</h3>
                    <ul>{bookArgumentMap.argument_chain.map((item) => <li key={item}>{item}</li>)}</ul>
                    <h3>{t.keyEvidence}</h3>
                    <ul>{bookArgumentMap.key_evidence.map((item) => <li key={item}>{item}</li>)}</ul>
                    <h3>{t.rebuttalsAndLimits}</h3>
                    <ul>{bookArgumentMap.rebuttals_and_limits.map((item) => <li key={item}>{item}</li>)}</ul>
                    <button type="button" onClick={() => void saveBookMap()} disabled={busy}>
                      {t.saveBookMap}
                    </button>
                  </section>
                ) : (
                  <p className="muted">{t.noMapResult}</p>
                )}
              </div>
            )}

            {mapMode === "onePageAccount" && (
              <div className="capture-form map-tool">
                <button type="button" onClick={() => void buildOnePageBookAccount()} disabled={busy}>
                  {t.buildOnePageAccount}
                </button>
                {onePageBookAccount ? (
                  <section className="feynman-result">
                    <h3>{t.onePageAccount}</h3>
                    <p>
                      {onePageBookAccount.title} · {onePageBookAccount.completed_count}/
                      {onePageBookAccount.chapter_count} · {onePageBookAccount.average_mastery}%
                    </p>
                    <h3>{t.coreAnswer}</h3>
                    <p>{onePageBookAccount.core_account}</p>
                    <h3>{t.argumentChain}</h3>
                    <ul>{onePageBookAccount.core_argument_chain.map((item) => <li key={item}>{item}</li>)}</ul>
                    <h3>{t.strongestEvidence}</h3>
                    <ul>{onePageBookAccount.strongest_evidence.map((item) => <li key={item}>{item}</li>)}</ul>
                    <h3>{t.weakPoints}</h3>
                    <ul>{onePageBookAccount.weak_points.map((item) => <li key={item}>{item}</li>)}</ul>
                    <h3>{t.applicationPrompts}</h3>
                    <ul>{onePageBookAccount.application_prompts.map((item) => <li key={item}>{item}</li>)}</ul>
                    <button type="button" onClick={() => void saveOnePageBookAccount()} disabled={busy}>
                      {t.saveOnePageAccount}
                    </button>
                  </section>
                ) : (
                  <p className="muted">{t.noMapResult}</p>
                )}
              </div>
            )}

            {mapMode === "evidenceTable" && (
              <div className="capture-form map-tool">
                <button type="button" onClick={() => void buildEvidenceTable()} disabled={busy}>
                  {t.buildEvidenceTable}
                </button>
                {evidenceTable ? (
                  <section className="feynman-result">
                    <h3>{t.evidenceTable}</h3>
                    <p>{evidenceTable.card_count} {t.evidence}</p>
                    {evidenceTable.cards.map((card) => (
                      <article key={`${card.claim}-${card.source_locator}`} className="recall-item">
                        <h3>{card.claim || t.claim}</h3>
                        <p><strong>{t.sourceLocator}</strong> {card.source_locator || "TBD"}</p>
                        <p><strong>{t.support}</strong> {card.support || "TBD"}</p>
                      </article>
                    ))}
                    <button type="button" onClick={() => void saveEvidenceTable()} disabled={busy}>
                      {t.saveEvidenceTable}
                    </button>
                  </section>
                ) : (
                  <p className="muted">{t.noMapResult}</p>
                )}
              </div>
            )}

            {mapMode === "conceptMap" && (
              <div className="capture-form map-tool">
                <button type="button" onClick={() => void buildConceptMap()} disabled={busy}>
                  {t.buildConceptMap}
                </button>
                {conceptMap ? (
                  <section className="feynman-result">
                    <h3>{t.nodes}</h3>
                    <ul>
                      {conceptMap.nodes.map((node) => (
                        <li key={node.id}>{node.label} ({node.type}, {node.mastery_score}%)</li>
                      ))}
                    </ul>
                    <h3>{t.links}</h3>
                    <ul>
                      {conceptMap.links.map((link) => (
                        <li key={`${link.source}-${link.relation}-${link.target}`}>
                          {link.source} - {link.relation} - {link.target}: {link.evidence}
                        </li>
                      ))}
                    </ul>
                    <button type="button" onClick={() => void saveConceptMap()} disabled={busy}>
                      {t.saveConceptMap}
                    </button>
                  </section>
                ) : (
                  <p className="muted">{t.noMapResult}</p>
                )}
              </div>
            )}

            {mapMode === "learning" && (
              <section className="learning-loop learning-panel map-tool">
                {status ? (
                  <>
                    <div className="learning-loop-metrics">
                      <p><strong>{status.learning_loop.average_mastery}%</strong><span>{t.averageMastery}</span></p>
                      <p><strong>{status.learning_loop.completed_count}</strong><span>{t.completedChapters}</span></p>
                      <p><strong>{status.learning_loop.review_ready.length}</strong><span>{t.reviewReady}</span></p>
                      <p><strong>{status.learning_loop.weak_chapters.length}</strong><span>{t.weakChapters}</span></p>
                    </div>
                    <div className="mastery-meter" aria-label={`${t.averageMastery} ${status.learning_loop.average_mastery}%`}>
                      <span style={{ width: `${status.learning_loop.average_mastery}%` }} />
                    </div>
                    {status.learning_loop.synthesis_due && <p className="success">{t.synthesisDue}</p>}
                  </>
                ) : (
                  <p className="muted">{t.noWorkspaceLoaded}</p>
                )}
              </section>
            )}
          </section>

          <aside className="map-detail">
            <header>
              <span className="eyebrow">{t.mapEvidenceSide}</span>
              <h2>{t.weakConcepts}</h2>
            </header>
            {status?.learning_loop.weak_concepts.length ? (
              <div className="weak-concept-list">
                {status.learning_loop.weak_concepts.map((item) => (
                  <button
                    key={`${item.chapter_id}-${item.concept}`}
                    type="button"
                    onClick={() => {
                      setMainView("reader");
                      void loadChapter(item.chapter_id);
                    }}
                    disabled={busy}
                    title={item.note}
                  >
                    <span>{item.concept}</span>
                    <em>{item.chapter_id}: {item.title}</em>
                  </button>
                ))}
              </div>
            ) : (
              <p className="muted">{t.noWeakConcepts}</p>
            )}
            <form className="weak-concept-form" onSubmit={addWeakConcept}>
              <label htmlFor="map-weak-concept">{t.weakConcept}</label>
              <input
                id="map-weak-concept"
                value={weakConcept}
                onChange={(event) => setWeakConcept(event.target.value)}
                placeholder={t.weakConceptPlaceholder}
              />
              <label htmlFor="map-weak-concept-chapter">{t.chapter}</label>
              <select
                id="map-weak-concept-chapter"
                value={weakConceptChapterId}
                onChange={(event) => setWeakConceptChapterId(event.target.value)}
              >
                {chapters.map((chapter) => (
                  <option key={chapter.id} value={chapter.id}>
                    {chapter.id}: {chapter.title}
                  </option>
                ))}
              </select>
              <label htmlFor="map-weak-concept-note">{t.weakConceptNote}</label>
              <textarea
                id="map-weak-concept-note"
                className="mini"
                value={weakConceptNote}
                onChange={(event) => setWeakConceptNote(event.target.value)}
                placeholder={t.weakConceptNotePlaceholder}
              />
              <button type="submit" disabled={busy || !weakConcept.trim() || !weakConceptChapterId}>
                {t.addWeakConcept}
              </button>
            </form>
            <div className="message-stack" aria-live="polite">
              {busy && <p className="muted">{t.working}</p>}
              {message && <p className="success">{message}</p>}
              {error && <p className="error">{error}</p>}
            </div>
          </aside>
        </div>
      )}

      {settingsOpen && llmProviders && (
        <div className="settings-overlay" onClick={() => setSettingsOpen(false)}>
          <form
            className="provider-settings settings-modal"
            onClick={(event) => event.stopPropagation()}
            onSubmit={saveLLMSettings}
          >
            <div className="settings-modal-header">
              <div>
                <span className="eyebrow">{t.providerSettings}</span>
                <h2>{t.settings}</h2>
              </div>
              <button type="button" onClick={() => setSettingsOpen(false)} aria-label={t.cancel}>
                ×
              </button>
            </div>

            <label htmlFor="llm-provider">{t.provider}</label>
            <select
              id="llm-provider"
              value={providerDraft}
              onChange={(event) => selectProviderDraft(event.target.value)}
              disabled={busy}
            >
              {llmProviders.providers.map((provider) => (
                <option key={provider.name} value={provider.name}>
                  {provider.display_name}
                </option>
              ))}
            </select>

            {llmProviders.providers
              .filter((provider) => provider.name === providerDraft)
              .map((provider) => (
                <div className="provider-details" key={provider.name}>
                  <p className={provider.configured ? "success" : "muted"}>
                    {provider.configured ? t.providerConfigured : t.providerNotConfigured}
                  </p>
                  {provider.api_key_env ? (
                    <>
                      <label htmlFor="llm-model">{t.providerModelEnv}</label>
                      <div className="model-picker-row">
                        <input
                          id="llm-model"
                          value={providerModelDraft}
                          onChange={(event) => setProviderModelDraft(event.target.value)}
                          placeholder={provider.model_env}
                          spellCheck={false}
                          list="llm-model-options"
                        />
                        <button
                          type="button"
                          onClick={() => void loadLLMModels(provider.name)}
                          disabled={busy || loadingProviderModels}
                        >
                          {t.providerModelRefresh}
                        </button>
                      </div>
                      <datalist id="llm-model-options">
                        {(providerModelCatalog?.models ?? provider.fallback_models).map((model) => (
                          <option key={model.value} value={model.value}>
                            {model.label}
                          </option>
                        ))}
                      </datalist>
                      {providerModelCatalog && (
                        <p className="muted">
                          {providerModelCatalog.source === "remote"
                            ? t.providerModelSourceRemote
                            : providerModelCatalog.reason === "auth"
                              ? t.providerModelSourceAuth
                              : providerModelCatalog.reason === "unavailable"
                                ? t.providerModelSourceUnavailable
                                : t.providerModelSourceFallback}
                        </p>
                      )}
                      <label htmlFor="llm-base-url">{t.providerBaseUrlEnv}</label>
                      <input
                        id="llm-base-url"
                        value={providerBaseUrlDraft}
                        onChange={(event) => setProviderBaseUrlDraft(event.target.value)}
                        placeholder={provider.base_url_env}
                        spellCheck={false}
                      />
                      <label htmlFor="llm-api-key">{t.providerApiKeyInput}</label>
                      <input
                        id="llm-api-key"
                        value={providerApiKeyDraft}
                        onChange={(event) => setProviderApiKeyDraft(event.target.value)}
                        placeholder={t.providerApiKeyPlaceholder}
                        type="password"
                        spellCheck={false}
                      />
                      <dl>
                        <div>
                          <dt>{t.providerKeyEnv}</dt>
                          <dd>{provider.api_key_env}</dd>
                        </div>
                      </dl>
                    </>
                  ) : (
                    <p className="muted">{t.providerLocalOnly}</p>
                  )}
                </div>
              ))}

            <div className="settings-actions">
              <button type="button" onClick={() => setSettingsOpen(false)}>
                {t.cancel}
              </button>
              <button type="submit" disabled={busy || !providerDraft}>
                {t.saveProviderSettings}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
