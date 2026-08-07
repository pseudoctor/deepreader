import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const desktopRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(desktopRoot, "../..");
const venvRoot = path.join(repoRoot, ".venv");
const runtimeRoot = path.join(desktopRoot, ".runtime", "python");
const runtimeBin = path.join(runtimeRoot, "bin");
const runtimeFrameworks = path.join(runtimeRoot, "Frameworks");
const runtimeLib = path.join(runtimeRoot, "lib");

function run(command, args, options = {}) {
  return execFileSync(command, args, { encoding: "utf8", stdio: "pipe", ...options }).trim();
}

function copyRecursive(source, destination, options = {}) {
  fs.rmSync(destination, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.cpSync(source, destination, { recursive: true, ...options });
}

function realPythonExecutable() {
  const venvPython = path.join(venvRoot, "bin", "python");
  if (!fs.existsSync(venvPython)) {
    throw new Error(`Missing virtualenv Python: ${venvPython}`);
  }
  return fs.realpathSync(venvPython);
}

function pythonFrameworkDependency(pythonExecutable) {
  const output = run("otool", ["-L", pythonExecutable]);
  const line = output
    .split("\n")
    .map((value) => value.trim())
    .find((value) => value.split(" ")[0].includes("Python.framework/") && value.split(" ")[0].endsWith("/Python"));
  if (!line) {
    throw new Error(`Could not find Python.framework dependency for ${pythonExecutable}`);
  }
  return line.split(" ")[0];
}

function frameworkRootFromDependency(frameworkPythonPath) {
  const marker = "Python.framework/";
  const index = frameworkPythonPath.indexOf(marker);
  if (index < 0) {
    throw new Error(`Unexpected Python framework path: ${frameworkPythonPath}`);
  }
  return frameworkPythonPath.slice(0, index + marker.length - 1);
}

function pythonFrameworkVersion(frameworkPythonPath) {
  const match = frameworkPythonPath.match(/Python\.framework\/Versions\/([^/]+)\/Python$/);
  if (!match) {
    throw new Error(`Could not determine Python.framework version: ${frameworkPythonPath}`);
  }
  return match[1];
}

function prepareRuntime() {
  const pythonExecutable = realPythonExecutable();
  const frameworkDependency = pythonFrameworkDependency(pythonExecutable);
  const frameworkRoot = frameworkRootFromDependency(frameworkDependency);
  const frameworkVersion = pythonFrameworkVersion(frameworkDependency);
  const venvLib = path.join(venvRoot, "lib");

  if (!fs.existsSync(venvLib)) {
    throw new Error(`Missing virtualenv lib directory: ${venvLib}`);
  }

  fs.rmSync(runtimeRoot, { recursive: true, force: true });
  fs.mkdirSync(runtimeBin, { recursive: true });

  copyRecursive(frameworkRoot, path.join(runtimeFrameworks, "Python.framework"), {
    verbatimSymlinks: true,
  });
  copyRecursive(venvLib, runtimeLib, { dereference: true });

  const runtimePythonName = `python${frameworkVersion}`;
  const runtimePython = path.join(runtimeBin, runtimePythonName);
  fs.copyFileSync(pythonExecutable, runtimePython);
  fs.chmodSync(runtimePython, 0o755);
  fs.symlinkSync(runtimePythonName, path.join(runtimeBin, "python3"));
  fs.symlinkSync(runtimePythonName, path.join(runtimeBin, "python"));

  const relativeFramework = `@executable_path/../Frameworks/Python.framework/Versions/${frameworkVersion}/Python`;
  run("install_name_tool", ["-change", frameworkDependency, relativeFramework, runtimePython]);
  run("codesign", ["--force", "--deep", "--sign", "-", path.join(runtimeFrameworks, "Python.framework")]);
  run("codesign", ["--force", "--sign", "-", runtimePython]);

  const check = run(runtimePython, [
    "-c",
    "import sys; import uvicorn; import deep_reading.api; print(sys.version.split()[0])",
  ], {
    env: {
      ...process.env,
      PYTHONPATH: [
        path.join(repoRoot, "scripts"),
        path.join(runtimeLib, `python${frameworkVersion}`, "site-packages"),
      ].join(path.delimiter),
    },
  });

  console.log(`Prepared Python runtime at ${runtimeRoot}`);
  console.log(`Python check: ${check}`);
}

prepareRuntime();
