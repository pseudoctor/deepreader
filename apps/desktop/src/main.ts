import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const isDev = Boolean(process.env.DEEP_READING_DESKTOP_DEV_SERVER);
const apiBaseUrl = process.env.DEEP_READING_API_BASE_URL ?? "http://127.0.0.1:8000";
const workspaceSelectChannel = "workspace:select-folder";
const obsidianSelectChannel = "obsidian:select-folder";
let backendProcess: ChildProcessWithoutNullStreams | null = null;

function webDistIndex(): string {
  return path.resolve(__dirname, "../../web/dist/index.html");
}

function repoRoot(): string {
  return path.resolve(__dirname, "../../..");
}

function pythonExecutable(): string {
  const venvPython = path.join(repoRoot(), ".venv", "bin", "python");
  return fs.existsSync(venvPython) ? venvPython : "python3";
}

async function isBackendHealthy(): Promise<boolean> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 500);
  try {
    const response = await fetch(`${apiBaseUrl}/health`, { signal: controller.signal });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

async function waitForBackend(): Promise<void> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    if (await isBackendHealthy()) return;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(`Deep Reading backend did not start at ${apiBaseUrl}`);
}

async function ensureBackend(): Promise<void> {
  if (await isBackendHealthy()) return;

  backendProcess = spawn(
    pythonExecutable(),
    ["-m", "uvicorn", "deep_reading.api:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: repoRoot(),
      env: {
        ...process.env,
        PYTHONPATH: path.join(repoRoot(), "scripts"),
      },
    },
  );

  backendProcess.stdout.on("data", (chunk) => {
    console.log(`[deep-reading-api] ${String(chunk).trim()}`);
  });
  backendProcess.stderr.on("data", (chunk) => {
    console.error(`[deep-reading-api] ${String(chunk).trim()}`);
  });
  backendProcess.on("exit", (code) => {
    console.log(`[deep-reading-api] exited with code ${code ?? "unknown"}`);
    backendProcess = null;
  });

  await waitForBackend();
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

app.whenReady().then(async () => {
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

  ipcMain.handle(obsidianSelectChannel, async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory", "createDirectory"],
      title: "Select Obsidian Export Folder",
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0];
  });

  try {
    await ensureBackend();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    dialog.showErrorBox("Deep Reading backend failed to start", message);
    console.error(error);
  }

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

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
