import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const desktopRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const electronBin = path.join(desktopRoot, "node_modules", ".bin", "electron");

const child = spawn(electronBin, ["dist/main.js"], {
  cwd: desktopRoot,
  env: {
    ...process.env,
    DEEP_READING_DESKTOP_DEV_SERVER:
      process.env.DEEP_READING_DESKTOP_DEV_SERVER ?? "http://127.0.0.1:5173/",
  },
  stdio: "inherit",
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
