import { contextBridge, ipcRenderer } from "electron";

const workspaceSelectChannel = "workspace:select-folder";
const sourceSelectChannel = "source:select-path";
const workspaceTargetSelectChannel = "workspace:select-target-folder";
const workspaceCreateChannel = "workspace:create-from-source";
const obsidianSelectChannel = "obsidian:select-folder";
const apiBaseUrl =
  process.env.DEEP_READING_DESKTOP_API_BASE_URL ??
  process.env.DEEP_READING_API_BASE_URL ??
  (process.env.DEEP_READING_DESKTOP_DEV_SERVER ? "/api" : "http://127.0.0.1:8000");

contextBridge.exposeInMainWorld("deepReadingDesktop", {
  apiBaseUrl,
  platform: process.platform,
  selectWorkspaceFolder: async (): Promise<string | null> => {
    return ipcRenderer.invoke(workspaceSelectChannel) as Promise<string | null>;
  },
  selectSourcePath: async (): Promise<string | null> => {
    return ipcRenderer.invoke(sourceSelectChannel) as Promise<string | null>;
  },
  selectWorkspaceTargetFolder: async (): Promise<string | null> => {
    return ipcRenderer.invoke(workspaceTargetSelectChannel) as Promise<string | null>;
  },
  createWorkspaceFromSource: async (
    sourcePath: string,
    workspacePath: string,
  ): Promise<string> => {
    return ipcRenderer.invoke(workspaceCreateChannel, {
      sourcePath,
      workspacePath,
    }) as Promise<string>;
  },
  selectObsidianFolder: async (): Promise<string | null> => {
    return ipcRenderer.invoke(obsidianSelectChannel) as Promise<string | null>;
  },
});
