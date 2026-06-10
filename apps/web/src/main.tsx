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
      setEvidenceLocator(`${chapter.id}: ${chapter.title}`);
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
      setMessage("Review card saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save review card");
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
      setMessage("Evidence card saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save evidence card");
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
          <span className="eyebrow">Capture</span>
          <h2>Build understanding</h2>
        </header>

        <div className="capture-tabs" role="tablist" aria-label="Capture type">
          {[
            ["note", "Note"],
            ["review", "Review"],
            ["evidence", "Evidence"],
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
        )}

        {activeCapture === "review" && (
          <form onSubmit={saveReviewCard} className="capture-form">
            <label htmlFor="review-question">Question</label>
            <textarea
              id="review-question"
              className="compact"
              value={reviewQuestion}
              onChange={(event) => setReviewQuestion(event.target.value)}
              placeholder="What should future me recall?"
            />

            <label htmlFor="review-answer">Answer</label>
            <textarea
              id="review-answer"
              value={reviewAnswer}
              onChange={(event) => setReviewAnswer(event.target.value)}
              placeholder="Write the answer in your own words..."
            />

            <button
              type="submit"
              disabled={busy || !reviewQuestion.trim() || !reviewAnswer.trim()}
            >
              Save review card
            </button>
          </form>
        )}

        {activeCapture === "evidence" && (
          <form onSubmit={saveEvidenceCard} className="capture-form">
            <label htmlFor="evidence-claim">Claim</label>
            <textarea
              id="evidence-claim"
              className="compact"
              value={evidenceClaim}
              onChange={(event) => setEvidenceClaim(event.target.value)}
              placeholder="What claim does this passage support?"
            />

            <label htmlFor="evidence-locator">Locator</label>
            <input
              id="evidence-locator"
              value={evidenceLocator}
              onChange={(event) => setEvidenceLocator(event.target.value)}
              spellCheck={false}
            />

            <label htmlFor="evidence-support">Support</label>
            <textarea
              id="evidence-support"
              value={evidenceSupport}
              onChange={(event) => setEvidenceSupport(event.target.value)}
              placeholder="Use a brief paraphrase or short excerpt..."
            />

            <label htmlFor="evidence-confidence">Confidence</label>
            <select
              id="evidence-confidence"
              value={evidenceConfidence}
              onChange={(event) => setEvidenceConfidence(event.target.value)}
            >
              <option>High</option>
              <option>Medium</option>
              <option>Low</option>
            </select>

            <label htmlFor="evidence-not-explicit">Not explicit</label>
            <textarea
              id="evidence-not-explicit"
              className="compact"
              value={evidenceNotExplicit}
              onChange={(event) => setEvidenceNotExplicit(event.target.value)}
              placeholder="What does the source not prove?"
            />

            <label htmlFor="evidence-inference">My inference</label>
            <textarea
              id="evidence-inference"
              className="compact"
              value={evidenceInference}
              onChange={(event) => setEvidenceInference(event.target.value)}
              placeholder="What are you inferring from it?"
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
              Save evidence card
            </button>
          </form>
        )}

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
