import assert from "node:assert/strict";
import { test } from "node:test";
import { createLayoutMenuItems } from "./menuConfig.js";

const findMenuItem = (items, path) => items.find((item) => item.path === path);

test("createLayoutMenuItems preserva itens principais do menu", () => {
  const items = createLayoutMenuItems();

  assert.equal(findMenuItem(items, "/dashboard")?.permission, "relatorios.gerencial");
  assert.equal(findMenuItem(items, "/pdv")?.permission, "vendas.criar");
  assert.equal(findMenuItem(items, "/financeiro")?.submenu?.some((item) => item.path === "/financeiro/vendas"), true);
  assert.equal(findMenuItem(items, "/veterinario")?.submenu?.some((item) => item.path === "/veterinario/agenda"), true);
});

test("createLayoutMenuItems aplica badge de lembretes conforme contador", () => {
  const semPendencias = createLayoutMenuItems({ lembretesCount: 0 });
  const comPendencias = createLayoutMenuItems({ lembretesCount: 2 });

  assert.equal(findMenuItem(semPendencias, "/lembretes")?.badge, false);
  assert.equal(findMenuItem(comPendencias, "/lembretes")?.badge, true);
});
