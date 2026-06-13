import type { Language, SelectionOutputLanguage } from "./i18n";
import type { WorkspaceLibraryItem } from "./types";

export function getInitialLanguage(): Language {
  const storedLanguage = window.localStorage.getItem("deep-reading-language");
  return storedLanguage === "zh" ? "zh" : "en";
}

export function getInitialObsidianFolder(): string {
  return window.localStorage.getItem("deep-reading-obsidian-folder") ?? "";
}

export function getInitialRecentWorkspaces(): string[] {
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

export function getInitialWorkspaceLibrary(): WorkspaceLibraryItem[] {
  try {
    const storedLibrary = window.localStorage.getItem("deep-reading-workspace-library");
    if (storedLibrary) {
      const parsed = JSON.parse(storedLibrary);
      if (Array.isArray(parsed)) {
        return parsed
          .filter(
            (item): item is WorkspaceLibraryItem =>
              typeof item === "object" &&
              item !== null &&
              typeof item.path === "string" &&
              typeof item.last_opened_at === "string",
          )
          .slice(0, 12);
      }
    }

    return getInitialRecentWorkspaces().map((path) => ({
      path,
      last_opened_at: new Date(0).toISOString(),
    }));
  } catch {
    return [];
  }
}

export function getInitialSelectionOutputLanguage(): SelectionOutputLanguage {
  const storedLanguage = window.localStorage.getItem("deep-reading-selection-output-language");
  return storedLanguage === "zh" || storedLanguage === "en" ? storedLanguage : "auto";
}
