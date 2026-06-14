export type Chapter = {
  id: string;
  title: string;
  line: number;
  state: string;
};

export type MainView = "reader" | "journal" | "map";

export type ReadingFontSize = "small" | "medium" | "large";

export type Status = {
  workspace: string;
  sources: number;
  words: number;
  estimated_tokens: number;
  current: string | null;
  progress: Record<string, number>;
  continue_reading: ContinueReading;
  learning_loop: LearningLoop;
  artifacts: Record<string, boolean>;
};

export type ChapterSummary = {
  id: string;
  title: string;
  state: string;
};

export type NextAction = {
  kind: "continue_current" | "review_completed" | "start_next" | "synthesize_book";
  chapter_id: string | null;
  title: string | null;
};

export type ContinueReading = {
  current_chapter: ChapterSummary | null;
  review_due: ChapterSummary[];
  next_action: NextAction;
};

export type LearningLoopChapter = ChapterSummary & {
  mastery_score: number;
  has_notes: boolean;
  has_active_recall: boolean;
  has_evidence: boolean;
  weak_reasons: string[];
};

export type WeakConcept = {
  concept: string;
  chapter_id: string;
  title: string;
  note: string;
};

export type LearningLoop = {
  chapters: LearningLoopChapter[];
  weak_chapters: LearningLoopChapter[];
  weak_concepts: WeakConcept[];
  review_ready: LearningLoopChapter[];
  synthesis_due: boolean;
  completed_count: number;
  average_mastery: number;
};

export type ChapterText = {
  id: string;
  title: string;
  line: number;
  text: string;
  reading_guide: {
    core_question: string;
    evidence_to_seek: string;
    recall_prompt: string;
  };
};

export type ObsidianExportResult = {
  vault_folder: string;
  mode: "learning_archive" | "full";
  markdown_files_exported: number;
  index_path: string;
  files: string[];
};

export type ObsidianExportMode = "learning_archive" | "full";

export type FeynmanCheckResult = {
  chapter_id: string;
  title: string;
  accurate_points: string[];
  vague_points: string[];
  missing_causal_links: string[];
  unsupported_leaps: string[];
  rewritten_version: string;
};

export type SelectionExplanationResult = {
  chapter_id: string;
  title: string;
  explanation: string;
};

export type SelectionReviewQuestionResult = {
  chapter_id: string;
  title: string;
  question: string;
  answer: string;
};

export type ChapterSynthesisResult = {
  start_chapter_id: string;
  chapter_count: number;
  chapters: ChapterSummary[];
  common_question: string;
  recurring_concepts: string[];
  argument_progression: string;
  open_questions: string[];
};

export type BookArgumentMapResult = {
  chapter_count: number;
  chapters: ChapterSummary[];
  core_problem: string;
  core_answer: string;
  argument_chain: string[];
  key_evidence: string[];
  rebuttals_and_limits: string[];
};

export type OnePageBookAccountResult = {
  title: string;
  chapter_count: number;
  completed_count: number;
  average_mastery: number;
  core_account: string;
  core_argument_chain: string[];
  strongest_evidence: string[];
  weak_points: string[];
  application_prompts: string[];
};

export type EvidenceTableCard = {
  claim: string;
  source_locator: string;
  support: string;
  confidence: string;
  not_explicit: string;
  inference: string;
};

export type EvidenceTableResult = {
  card_count: number;
  cards: EvidenceTableCard[];
};

export type EvidenceContextMatch = {
  source_type: "chapter" | "evidence_card" | "chapter_note";
  locator: string;
  chapter_id: string | null;
  title: string | null;
  snippet: string;
  score: number;
};

export type EvidenceContextResult = {
  query: string;
  matches: EvidenceContextMatch[];
};

export type LearningJournalItem = {
  id: string;
  kind: string;
  chapter_id: string | null;
  title: string;
  locator: string;
  content: string;
  source_path: string;
  target_text?: string;
  editable?: boolean;
  block_start?: number;
  block_end?: number;
};

export type LearningJournalResult = {
  workspace: string;
  items: LearningJournalItem[];
  groups: Record<string, number>;
  chapters: ChapterSummary[];
};

export type LearningJournalFilter = {
  kind: string;
  chapter_id: string;
};

export type WorkspaceLibraryItem = {
  path: string;
  last_opened_at: string;
  title?: string;
  current?: string | null;
  progress?: Record<string, number>;
  next_action?: NextAction;
  average_mastery?: number;
  review_ready_count?: number;
  weak_count?: number;
};

export type ConceptMapNode = {
  id: string;
  label: string;
  type: string;
  state: string;
  mastery_score: number;
};

export type ConceptMapLink = {
  source: string;
  target: string;
  relation: string;
  evidence: string;
};

export type ConceptMapResult = {
  node_count: number;
  link_count: number;
  nodes: ConceptMapNode[];
  links: ConceptMapLink[];
};

export type ActiveRecallQuestion = {
  question: string;
  answer_hint: string;
};

export type ActiveRecallResult = {
  chapter_id: string;
  title: string;
  state: string;
  questions: ActiveRecallQuestion[];
  eligible_for_review: boolean;
  chapter_count: number;
};

export type SelectionToolbarPosition = {
  left: number;
  top: number;
};

export type LLMProviderStatus = {
  name: string;
  display_name: string;
  configured: boolean;
  api_key_env: string | null;
  api_key_present: boolean;
  base_url_env: string;
  base_url: string | null;
  model_env: string;
  model: string;
  fallback_models: LLMModelOption[];
  selected_env: string;
};

export type LLMProviderList = {
  selected: string;
  providers: LLMProviderStatus[];
};

export type LLMModelOption = {
  value: string;
  label: string;
};

export type LLMModelCatalog = {
  provider: string;
  models: LLMModelOption[];
  source: "remote" | "fallback";
  reason: string | null;
};
