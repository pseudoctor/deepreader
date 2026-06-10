import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("deepReadingDesktop", {
  platform: process.platform,
});
