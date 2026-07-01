import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const checks = [
  ["src/components/ui/Panel.jsx", ["dark:border-slate-700", "dark:bg-slate-900", "dark:text-slate-100"]],
  ["src/components/ui/DataTable.jsx", ["dark:bg-slate-900", "dark:bg-slate-800", "dark:border-slate-800"]],
  ["src/components/ui/MetricCard.jsx", ["dark:border", "dark:bg", "dark:text"]],
  ["src/components/ui/PageHeader.jsx", ["dark:bg", "dark:text-slate-100", "dark:text-slate-400"]],
  ["src/components/ui/FormField.jsx", ["dark:border-slate-700", "dark:bg-slate-900", "dark:text-slate-100"]],
  ["src/components/ui/FilterBar.jsx", ["dark:border-slate-700"]],
  ["src/components/ui/PaginationControls.jsx", ["dark:border-slate-700", "dark:bg-slate-900", "dark:text-slate-300"]],
  ["src/components/ui/SegmentedControl.jsx", ["dark:bg-slate-900", "dark:text-slate-300"]],
  ["src/components/ui/AutocompleteSelect.jsx", ["dark:border-slate-700", "dark:bg-slate-900", "dark:text-slate-100"]],
  ["src/components/ui/EmptyState.jsx", ["dark:border-slate-700", "dark:bg-slate-900", "dark:text-slate-400"]],
  ["src/components/ui/EntityCard.jsx", ["dark:border-slate-700", "dark:bg-slate-900", "dark:text-slate-100"]],
  ["src/components/ui/actionStyles.js", ["dark:disabled", "dark:border", "dark:bg"]],
];

for (const [relativePath, fragments] of checks) {
  const content = readFileSync(new URL(`../${relativePath}`, import.meta.url), "utf8");
  for (const fragment of fragments) {
    assert.ok(content.includes(fragment), `${relativePath} missing ${fragment}`);
  }
}

console.log("ui dark classes contract ok");
