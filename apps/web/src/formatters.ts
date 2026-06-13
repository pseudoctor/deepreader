import type { ChapterSynthesisResult, FeynmanCheckResult } from "./types";

export function formatFeynmanFeedback(result: FeynmanCheckResult): string {
  const list = (items: string[]) =>
    items.length > 0 ? items.map((item) => `- ${item}`).join("\n") : "- None";
  return [
    "## Feynman Check",
    "",
    "### Accurate",
    list(result.accurate_points),
    "",
    "### Too Vague",
    list(result.vague_points),
    "",
    "### Missing Causal Links",
    list(result.missing_causal_links),
    "",
    "### Unsupported Leaps",
    list(result.unsupported_leaps),
    "",
    "### Rewrite",
    result.rewritten_version,
  ].join("\n");
}

export function formatChapterSynthesis(result: ChapterSynthesisResult): string {
  const list = (items: string[]) => items.map((item) => `- ${item}`).join("\n");
  return [
    "## Cross-Chapter Synthesis",
    "",
    "### Chapters",
    list(result.chapters.map((chapter) => `${chapter.id}: ${chapter.title} (${chapter.state})`)),
    "",
    "### Common Question",
    result.common_question,
    "",
    "### Recurring Concepts",
    list(result.recurring_concepts),
    "",
    "### Argument Progression",
    result.argument_progression,
    "",
    "### Open Questions",
    list(result.open_questions),
  ].join("\n");
}
