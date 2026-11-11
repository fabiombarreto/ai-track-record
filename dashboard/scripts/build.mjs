// Build the dashboard from the publication export named by ATR_EXPORT_DIR (D-020, D-033, D-060).
// Preflight first, then a clean build with telemetry off, run from the pinned Framework.
import {spawnSync} from "node:child_process";
import {readFileSync, rmSync} from "node:fs";
import {dirname, join, resolve} from "node:path";
import {fileURLToPath} from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

// 1. Preflight: the export must be complete before anything else runs.
const preflight = spawnSync("python3", [join(root, "loaders", "exportdir.py")], {
  stdio: "inherit",
  env: process.env
});
if (preflight.error) {
  console.error(`could not run python3: ${preflight.error.message}`);
  process.exit(1);
}
if (preflight.status !== 0) process.exit(preflight.status ?? 1);

// 2. A leftover build or loader cache from another export must never be reused.
rmSync(join(root, "dist"), {recursive: true, force: true});
rmSync(join(root, "src", ".observablehq", "cache"), {recursive: true, force: true});

// 3. Locate the Framework executable without relying on .bin symlinks.
const frameworkDir = join(root, "node_modules", "@observablehq", "framework");
const {bin} = JSON.parse(readFileSync(join(frameworkDir, "package.json"), "utf8"));
const executable = join(frameworkDir, typeof bin === "string" ? bin : bin.observable);

// 4. Run the build with telemetry disabled by this script, not by the operator's shell.
const build = spawnSync(process.execPath, [executable, "build"], {
  cwd: root,
  stdio: "inherit",
  env: {
    ...process.env,
    OBSERVABLE_TELEMETRY_DISABLE: "1"
  }
});
if (build.error) {
  console.error(`could not run the Framework build: ${build.error.message}`);
  process.exit(1);
}

// 5. Report the Framework's own status.
process.exit(build.status ?? 1);
