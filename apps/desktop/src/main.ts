import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import path from "node:path";

const isDev = Boolean(process.env.DEEP_READING_DESKTOP_DEV_SERVER);
const workspaceSelectChannel = "workspace:select-folder";

function webDistIndex(): string {
  return path.resolve(__dirname, "../../web/dist/index.html");
}

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 980,
    minHeight: 640,
    title: "Deep Reading",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  window.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev) {
    void window.loadURL(process.env.DEEP_READING_DESKTOP_DEV_SERVER as string);
    window.webContents.openDevTools({ mode: "detach" });
    return;
  }

  void window.loadFile(webDistIndex());
}

app.whenReady().then(() => {
  ipcMain.handle(workspaceSelectChannel, async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory"],
      title: "Select Reading Workspace",
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0];
  });

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
