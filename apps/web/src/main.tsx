import React, { FormEvent, useMemo, useState } from "react";
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

const defaultWorkspace = "workspaces/guns-germs-steel-reading";

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
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
  const [workspace, setWorkspace] = useState(defaultWorkspace);
  const [status, setStatus] = useState<Status | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [activeChapter, setActiveChapter] = useState<ChapterText | null>(null);
  const [noteSection, setNoteSection] = useState("Confusions");
  const [noteText, setNoteText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const progressText = useMemo(() => {
    if (!status) return "No workspace loaded";
    return Object.entries(status.progress)
      .map(([key, value]) => `${key}: ${value}`)
      .join(" · ");
  }, [status]);

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
      setMessage("Workspace loaded");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workspace");
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chapter");
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
      setMessage(`${activeChapter.id} marked ${nextState}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update state");
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
      setMessage("Note saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save note");
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
            <h1>Deep Reading</h1>
            <p>Workspace reader</p>
          </div>
        </header>

        <form
          className="workspace-form"
          onSubmit={(event) => {
            event.preventDefault();
            void loadWorkspace();
          }}
        >
          <label htmlFor="workspace">Workspace</label>
          <input
            id="workspace"
            value={workspace}
            onChange={(event) => setWorkspace(event.target.value)}
            spellCheck={false}
          />
          <button type="submit" disabled={busy}>
            Load
          </button>
        </form>

        <div className="status-block">
          <span>Status</span>
          <strong>{progressText}</strong>
        </div>

        <nav className="chapter-list" aria-label="Chapters">
          {chapters.map((chapter) => (
            <button
              key={chapter.id}
              className={activeChapter?.id === chapter.id ? "active" : ""}
              onClick={() => void loadChapter(chapter.id)}
              type="button"
            >
              <span>{chapter.id}</span>
              <strong>{chapter.title}</strong>
              <em>{chapter.state}</em>
            </button>
          ))}
        </nav>
      </aside>

      <section className="reader-pane">
        <div className="reader-toolbar">
          <div>
            <span className="eyebrow">Chapter</span>
            <h2>{activeChapter ? `${activeChapter.id}: ${activeChapter.title}` : "No chapter"}</h2>
          </div>
          <div className="state-actions">
            {["reading", "done", "review"].map((stateName) => (
              <button
                key={stateName}
                onClick={() => void updateState(stateName)}
                disabled={!activeChapter || busy}
                type="button"
              >
                {stateName}
              </button>
            ))}
          </div>
        </div>

        <article className="chapter-text">
          {activeChapter ? activeChapter.text : "Load a workspace to start reading."}
        </article>
      </section>

      <aside className="notes-pane">
        <header>
          <span className="eyebrow">Notes</span>
          <h2>Capture while reading</h2>
        </header>

        <form onSubmit={saveNote} className="note-form">
          <label htmlFor="section">Section</label>
          <select
            id="section"
            value={noteSection}
            onChange={(event) => setNoteSection(event.target.value)}
          >
            <option>Confusions</option>
            <option>Key Concepts</option>
            <option>My 3-5 Sentence Summary</option>
            <option>Applications</option>
          </select>

          <label htmlFor="note">Note</label>
          <textarea
            id="note"
            value={noteText}
            onChange={(event) => setNoteText(event.target.value)}
            placeholder="Write a question, summary, or application..."
          />

          <button type="submit" disabled={!activeChapter || busy || !noteText.trim()}>
            Save note
          </button>
        </form>

        <div className="message-stack" aria-live="polite">
          {busy && <p className="muted">Working...</p>}
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
