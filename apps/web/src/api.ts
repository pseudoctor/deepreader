type DeepReadingDesktopApi = {
  apiBaseUrl: string;
  apiToken: string;
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
  const apiToken = window.deepReadingDesktop?.apiToken;
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (apiToken) {
    headers.set("X-Deep-Reading-API-Token", apiToken);
  }
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
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
  const apiToken = window.deepReadingDesktop?.apiToken;
  const query = new URLSearchParams({ filename: file.name });
  if (workspacePath.trim()) {
    query.set("workspace", workspacePath.trim());
  }
  const response = await fetch(`${apiBaseUrl}/workspaces/import?${query.toString()}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/octet-stream",
      ...(apiToken ? { "X-Deep-Reading-API-Token": apiToken } : {}),
    },
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
  const apiToken = window.deepReadingDesktop?.apiToken;
  const query = new URLSearchParams({ workspace: workspacePath });
  const response = await fetch(`${apiBaseUrl}/workspaces?${query.toString()}`, {
    method: "DELETE",
    headers: apiToken ? { "X-Deep-Reading-API-Token": apiToken } : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data as { deleted: string };
}
