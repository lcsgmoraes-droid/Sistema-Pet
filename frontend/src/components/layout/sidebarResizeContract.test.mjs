import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const sidebarSource = readFileSync(new URL("./LayoutSidebar.jsx", import.meta.url), "utf8");
const menuSource = readFileSync(new URL("./SidebarMenu.jsx", import.meta.url), "utf8");

test("sidebar mostra uma alca visivel para ajustar a largura", () => {
  assert.match(sidebarSource, /Ajustar largura do menu lateral/);
  assert.match(sidebarSource, /data-sidebar-resize-handle/);
  assert.match(sidebarSource, /Arraste para aumentar ou diminuir/);
  assert.match(sidebarSource, /bg-\[#0f8b8d\]\/45/);
});

test("nomes truncados mostram o texto completo ao passar o mouse", () => {
  assert.match(menuSource, /text\.scrollWidth > text\.clientWidth/);
  assert.match(menuSource, /role="tooltip"/);
  assert.match(menuSource, /title=\{item\.label\}/);
});
