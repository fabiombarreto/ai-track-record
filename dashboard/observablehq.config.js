import {readFileSync} from "node:fs";
import {join} from "node:path";
import {runSlugs} from "./src/components/runs.js";

// Observable Framework configuration for the dashboard (D-025, D-060).
// The "light" and "dark" entries follow the reader's colour preference; "dashboard"
// is the Framework's wide grid layout. Nothing here sends data anywhere.
export default {
  root: "src",
  title: "AI Track Record",
  pages: [
    {name: "Runs", path: "/runs"},
    {name: "Grid", path: "/grid"},
    {name: "Tasks", path: "/tasks"},
    {name: "Methodology", path: "/methodology"}
  ],
  theme: ["light", "dark", "dashboard"],
  footer: "",
  // One page per exported run, read when the build asks for the paths (D-020).
  dynamicPaths: async function* () {
    const dir = process.env.ATR_EXPORT_DIR;
    if (!dir) throw new Error("ATR_EXPORT_DIR is not set; point it at a publication export directory");
    let runs;
    try {
      runs = JSON.parse(readFileSync(join(dir, "runs.json"), "utf8"));
    } catch (error) {
      throw new Error(`cannot read runs.json from ATR_EXPORT_DIR: ${error.message}`);
    }
    if (!Array.isArray(runs)) throw new Error("runs.json in ATR_EXPORT_DIR is not a list");
    for (const slug of runSlugs(runs)) yield `/run/${slug}`;
  }
};
