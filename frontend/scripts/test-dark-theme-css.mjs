import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../src/index.css", import.meta.url), "utf8");

for (const expected of [
  "--color-app-bg",
  "--color-surface",
  "--color-chart-grid",
  ".dark .bg-white",
  ".dark .text-gray-900",
  ".dark .border-gray-200",
  ".dark input",
  ".dark .recharts-cartesian-grid",
  ".corepet-toast",
]) {
  assert.ok(css.includes(expected), `Missing ${expected}`);
}

console.log("dark theme css contract ok");
