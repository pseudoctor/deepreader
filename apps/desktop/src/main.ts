import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";

const isDev = Boolean(process.env.DEEP_READING_DESKTOP_DEV_SERVER);
const explicitApiBaseUrl = process.env.DEEP_READING_API_BASE_URL;
let apiBaseUrl = explicitApiBaseUrl ?? "";
const workspaceSelectChannel = "workspace:select-folder";
const sourceSelectChannel = "source:select-path";
const workspaceTargetSelectChannel = "workspace:select-target-folder";
const workspaceCreateChannel = "workspace:create-from-source";
const obsidianSelectChannel = "obsidian:select-folder";
let backendProcess: ChildProcessWithoutNullStreams | null = null;

function webDistIndex(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "web", "dist", "index.html");
  }

  return path.resolve(__dirname, "../../web/dist/index.html");
}

function repoRoot(): string {
  return path.resolve(__dirname, "../../..");
}

function scriptsRoot(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "scripts");
  }

  return path.join(repoRoot(), "scripts");
}

function bundledSitePackagesRoots(): string[] {
  if (!app.isPackaged) {
    return [];
  }

  const libRoot = path.join(process.resourcesPath, "python", "lib");
  if (!fs.existsSync(libRoot)) {
    return [];
  }

  return fs
    .readdirSync(libRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(libRoot, entry.name, "site-packages"))
    .filter((candidate) => fs.existsSync(candidate));
}

function pythonCandidates(): string[] {
  const candidates = [];

  if (app.isPackaged) {
    candidates.push(
      path.join(process.resourcesPath, "python", "bin", "python3"),
      path.join(process.resourcesPath, "python", "bin", "python"),
    );
  }

  candidates.push(path.join(repoRoot(), ".venv", "bin", "python"), "python3");
  return candidates;
}

function backendEnv(): NodeJS.ProcessEnv {
  return {
    ...process.env,
    DEEP_READING_DESKTOP_API_BASE_URL: apiBaseUrl,
    DEEP_READING_LLM_SETTINGS_PATH:
      process.env.DEEP_READING_LLM_SETTINGS_PATH ?? path.join(app.getPath("userData"), "llm_settings.json"),
    PYTHONPATH: [scriptsRoot(), ...bundledSitePackagesRoots()].join(path.delimiter),
  };
}

function runPythonCheck(executable: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const child = spawn(
      executable,
      [
        "-c",
        "import uvicorn; import deep_reading.api; print('deep-reading-backend-ok')",
      ],
      {
        cwd: app.isPackaged ? process.resourcesPath : repoRoot(),
        env: backendEnv(),
      },
    );
    const stderr: string[] = [];

    child.stderr.on("data", (chunk) => {
      stderr.push(String(chunk));
    });

    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }

      reject(new Error(stderr.join("").trim() || `Python backend check failed with code ${code}`));
    });
  });
}

async function verifyBackendRuntime(): Promise<string> {
  const attempts = [];
  for (const candidate of pythonCandidates()) {
    if (candidate !== "python3" && !fs.existsSync(candidate)) {
      attempts.push(`${candidate}: not found`);
      continue;
    }

    try {
      await runPythonCheck(candidate);
      return candidate;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      attempts.push(`${candidate}: ${message}`);
    }
  }

  throw new Error(
    [
      "Deep Reading could not find a Python runtime with the required backend modules.",
      "Required imports: uvicorn and deep_reading.api.",
      "",
      "Checked:",
      ...attempts.map((attempt) => `- ${attempt}`),
    ].join("\n"),
  );
}

async function isBackendHealthy(): Promise<boolean> {
  if (!apiBaseUrl) {
    return false;
  }

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

function findAvailablePort(host = "127.0.0.1"): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, host, () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close(() => reject(new Error("Could not allocate a local backend port.")));
        return;
      }
      const port = address.port;
      server.close(() => resolve(port));
    });
  });
}

async function waitForBackend(): Promise<void> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    if (await isBackendHealthy()) return;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(`Deep Reading backend did not start at ${apiBaseUrl}`);
}

async function ensureBackend(): Promise<void> {
  if (explicitApiBaseUrl) {
    apiBaseUrl = explicitApiBaseUrl;
    if (await isBackendHealthy()) return;
    throw new Error(`Configured Deep Reading backend is not reachable at ${apiBaseUrl}`);
  }

  const backendPython = await verifyBackendRuntime();
  const backendPort = await findAvailablePort();
  apiBaseUrl = `http://127.0.0.1:${backendPort}`;
  process.env.DEEP_READING_DESKTOP_API_BASE_URL = apiBaseUrl;
  backendProcess = spawn(
    backendPython,
    ["-m", "uvicorn", "deep_reading.api:app", "--host", "127.0.0.1", "--port", String(backendPort)],
    {
      cwd: app.isPackaged ? process.resourcesPath : repoRoot(),
      env: backendEnv(),
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

async function createWorkspaceFromSource(sourcePath: string, workspacePath: string): Promise<string> {
  const backendPython = await verifyBackendRuntime();
  return new Promise((resolve, reject) => {
    const child = spawn(
      backendPython,
      ["-m", "deep_reading.cli", "init", sourcePath, "--workspace", workspacePath],
      {
        cwd: app.isPackaged ? process.resourcesPath : repoRoot(),
        env: backendEnv(),
      },
    );
    const stderr: string[] = [];

    child.stderr.on("data", (chunk) => {
      stderr.push(String(chunk));
    });

    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve(workspacePath);
        return;
      }

      reject(new Error(stderr.join("").trim() || `Workspace creation failed with code ${code}`));
    });
  });
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
    try {
      const protocol = new URL(url).protocol;
      if (protocol === "http:" || protocol === "https:") {
        void shell.openExternal(url);
      }
    } catch {
      return { action: "deny" };
    }
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

  ipcMain.handle(sourceSelectChannel, async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openFile", "openDirectory"],
      title: "Select Book Or Source Folder",
      filters: [
        {
          name: "Readable Sources",
          extensions: [
            "pdf",
            "epub",
            "docx",
            "txt",
            "text",
            "md",
            "markdown",
            "html",
            "htm",
            "rtf",
          ],
        },
        { name: "All Files", extensions: ["*"] },
      ],
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0];
  });

  ipcMain.handle(workspaceTargetSelectChannel, async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory", "createDirectory"],
      title: "Select Workspace Folder",
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0];
  });

  ipcMain.handle(
    workspaceCreateChannel,
    async (_event, request: { sourcePath: string; workspacePath: string }) => {
      if (!request.sourcePath || !request.workspacePath) {
        throw new Error("Source path and workspace path are required.");
      }

      return createWorkspaceFromSource(request.sourcePath, request.workspacePath);
    },
  );

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
