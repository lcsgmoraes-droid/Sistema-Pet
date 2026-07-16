import assert from "node:assert/strict";
import { test } from "node:test";
import { createLayoutMenuItems } from "./menuConfig.js";

const findMenuItem = (items, path) => items.find((item) => item.path === path);

test("createLayoutMenuItems preserva itens principais do menu", () => {
  const items = createLayoutMenuItems();

  assert.equal(findMenuItem(items, "/dashboard")?.permission, "relatorios.gerencial");
  assert.equal(findMenuItem(items, "/dashboard-gerencial"), undefined);
  assert.equal(findMenuItem(items, "/pdv")?.permission, "vendas.criar");
  assert.equal(
    findMenuItem(items, "/financeiro")?.submenu?.some((item) => item.path === "/financeiro/vendas"),
    true,
  );
  assert.equal(
    findMenuItem(items, "/veterinario")?.submenu?.some(
      (item) => item.path === "/veterinario/agenda",
    ),
    true,
  );
});

test("createLayoutMenuItems organiza a rotina e agrupa as telas do Bling", () => {
  const items = createLayoutMenuItems();
  const visiblePaths = items.map((item) => item.path);
  const bling = findMenuItem(items, "/vendas/bling");
  const pathsBySection = (section) =>
    items.filter((item) => item.section === section).map((item) => item.path);

  assert.deepEqual(visiblePaths.slice(0, 3), ["/dashboard", "/lembretes", "/clientes"]);
  assert.equal(findMenuItem(items, "/dashboard")?.section, "Visão geral");
  assert.equal(findMenuItem(items, "/pdv")?.section, "Vendas e relacionamento");
  assert.deepEqual(
    bling?.submenu?.map((item) => item.path),
    ["/vendas/bling-pedidos", "/vendas/bling-monitor"],
  );
  assert.deepEqual(pathsBySection("Vendas e relacionamento"), [
    "/pdv",
    "/ecommerce",
    "/campanhas",
    "/vendas/bling",
    "/entregas",
  ]);
  assert.deepEqual(pathsBySection("Gestão"), [
    "/cadastros",
    "/rh",
    "/ia",
    "/admin",
    "/configuracoes",
  ]);
  assert.equal(findMenuItem(items, "/configuracoes")?.section, "Gestão");
});

test("createLayoutMenuItems aplica badge de lembretes conforme contador", () => {
  const semPendencias = createLayoutMenuItems({ lembretesCount: 0 });
  const comPendencias = createLayoutMenuItems({ lembretesCount: 2 });

  assert.equal(findMenuItem(semPendencias, "/lembretes")?.badge, false);
  assert.equal(findMenuItem(comPendencias, "/lembretes")?.badge, true);
});
