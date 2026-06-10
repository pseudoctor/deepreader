import { contextBridge, ipcRenderer } from "electron";

const workspaceSelectChannel = "workspace:select-folder";
const obsidianSelectChannel = "obsidian:select-folder";

contextBridge.exposeInMainWorld("deepReadingDesktop", {
  platform: process.platform,
  selectWorkspaceFolder: async (): Promise<string | null> => {
    return ipcRenderer.invoke(workspaceSelectChannel) as Promise<string | null>;
  },
  selectObsidianFolder: async (): Promise<string | null> => {
    return ipcRenderer.invoke(obsidianSelectChannel) as Promise<string | null>;
  },
});
