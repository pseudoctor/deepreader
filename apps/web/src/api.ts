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
