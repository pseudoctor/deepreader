import { contextBridge, ipcRenderer } from "electron";

const workspaceSelectChannel = "workspace:select-folder";
const obsidianSelectChannel = "obsidian:select-folder";
const apiBaseUrl =
  process.env.DEEP_READING_API_BASE_URL ??
  (process.env.DEEP_READING_DESKTOP_DEV_SERVER ? "/api" : "http://127.0.0.1:8000");

contextBridge.exposeInMainWorld("deepReadingDesktop", {
  apiBaseUrl,
  platform: process.platform,
  selectWorkspaceFolder: async (): Promise<string | null> => {
    return ipcRenderer.invoke(workspaceSelectChannel) as Promise<string | null>;
  },
  selectObsidianFolder: async (): Promise<string | null> => {
    return ipcRenderer.invoke(obsidianSelectChannel) as Promise<string | null>;
  },
});
