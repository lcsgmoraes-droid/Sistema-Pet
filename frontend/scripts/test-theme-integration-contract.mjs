import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
const layout = readFileSync(new URL("../src/components/Layout.jsx", import.meta.url), "utf8");
const opsLayout = readFileSync(new URL("../src/components/OpsLayout.jsx", import.meta.url), "utf8");
const indexHtml = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const themeContext = readFileSync(
  new URL("../src/theme/ThemeContext.jsx", import.meta.url),
  "utf8",
);
const toggle = readFileSync(
  new URL("../src/components/theme/ThemeToggle.jsx", import.meta.url),
  "utf8",
);

assert.ok(app.includes("ThemeProvider"), "App must wrap routes in ThemeProvider");
assert.ok(layout.includes("ThemeToggle"), "Main layout must expose ThemeToggle");
assert.ok(opsLayout.includes("ThemeToggle"), "Ops layout must expose ThemeToggle");
assert.ok(
  indexHtml.includes("corepet_theme"),
  "index.html must apply stored theme before React paints",
);
assert.ok(themeContext.includes("useTheme"), "ThemeContext must export useTheme");
assert.ok(toggle.includes("aria-pressed"), "ThemeToggle must expose pressed state");
assert.ok(toggle.includes("Moon") && toggle.includes("Sun"), "ThemeToggle must use moon/sun icons");

console.log("theme integration contract ok");
