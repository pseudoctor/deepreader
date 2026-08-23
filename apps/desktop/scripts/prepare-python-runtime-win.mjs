import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.platform !== "win32") {
  throw new Error("Windows runtime preparation must run on Windows");
}

const desktopRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(desktopRoot, "../..");
const venvRoot = path.join(repoRoot, ".venv");
const runtimeRoot = path.join(desktopRoot, ".runtime", "python");

function run(command, args, options = {}) {
  return execFileSync(command, args, { encoding: "utf8", stdio: "pipe", ...options }).trim();
}

function prepareRuntime() {
  const venvPython = path.join(venvRoot, "Scripts", "python.exe");
  const venvSitePackages = path.join(venvRoot, "Lib", "site-packages");
  if (!fs.existsSync(venvPython)) {
    throw new Error(`Missing Windows virtualenv Python: ${venvPython}`);
  }
  if (!fs.existsSync(venvSitePackages)) {
    throw new Error(`Missing Windows virtualenv packages: ${venvSitePackages}`);
  }

  const basePrefix = path.resolve(run(venvPython, ["-c", "import sys; print(sys.base_prefix)"]));
  const basePython = path.join(basePrefix, "python.exe");
  if (!fs.existsSync(basePython)) {
    throw new Error(`Missing base Python executable: ${basePython}`);
  }

  fs.rmSync(runtimeRoot, { recursive: true, force: true });
  fs.cpSync(basePrefix, runtimeRoot, { recursive: true, dereference: true });

  const runtimeSitePackages = path.join(runtimeRoot, "Lib", "site-packages");
  fs.rmSync(runtimeSitePackages, { recursive: true, force: true });
  fs.cpSync(venvSitePackages, runtimeSitePackages, { recursive: true, dereference: true });

  const runtimePython = path.join(runtimeRoot, "python.exe");
  const pythonVersion = run(runtimePython, ["-c", "import sys; print(sys.version.split()[0])"]);
  const check = run(runtimePython, [
    "-c",
    "import uvicorn; import deep_reading.api; print('deep-reading-backend-ok')",
  ], {
    env: {
      ...process.env,
      PYTHONPATH: [path.join(repoRoot, "scripts"), runtimeSitePackages].join(path.delimiter),
    },
  });

  console.log(`Prepared Windows Python runtime at ${runtimeRoot}`);
  console.log(`Python check: ${pythonVersion} (${check})`);
}

prepareRuntime();
