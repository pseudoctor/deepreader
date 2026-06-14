type DeepReadingDesktopApi = {
  apiBaseUrl: string;
  platform: string;
  selectWorkspaceFolder: () => Promise<string | null>;
  selectSourcePath: () => Promise<string | null>;
  selectWorkspaceTargetFolder: () => Promise<string | null>;
  createWorkspaceFromSource: (sourcePath: string, workspacePath: string) => Promise<string>;
  selectObsidianFolder: () => Promise<string | null>;
};

declare global {
  interface Window {
    deepReadingDesktop?: DeepReadingDesktopApi;
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
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

export async function importWorkspaceSource(
  file: File,
  workspacePath: string,
): Promise<{ workspace: string }> {
  const apiBaseUrl = window.deepReadingDesktop?.apiBaseUrl ?? "/api";
  const query = new URLSearchParams({ filename: file.name });
  if (workspacePath.trim()) {
    query.set("workspace", workspacePath.trim());
  }
  const response = await fetch(`${apiBaseUrl}/workspaces/import?${query.toString()}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: await file.arrayBuffer(),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data as { workspace: string };
}

export async function deleteWorkspace(workspacePath: string): Promise<{ deleted: string }> {
  const apiBaseUrl = window.deepReadingDesktop?.apiBaseUrl ?? "/api";
  const query = new URLSearchParams({ workspace: workspacePath });
  const response = await fetch(`${apiBaseUrl}/workspaces?${query.toString()}`, {
    method: "DELETE",
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data as { deleted: string };
}
