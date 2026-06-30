import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MAX_MENU_FAVORITES,
  buildVisibleMenuFavorites,
  flattenMenuItemsForFavorites,
  normalizeMenuFavorites,
  reorderMenuFavorites,
  shouldBlockFavoriteShortcutClick,
  toggleMenuFavorite,
} from "../src/components/layout/menuFavorites.js";

const menuItems = [
  {
    path: "/produtos",
    label: "Produtos / Estoque",
    iconKey: "package",
    submenu: [
      { path: "/produtos", label: "Listar Produtos", iconKey: "package" },
      { path: "/produtos/balanco", label: "Balanco", iconKey: "clipboard-list" },
    ],
  },
  { path: "/pdv", label: "PDV (Vendas)", iconKey: "shopping-cart" },
];

test("flattenMenuItemsForFavorites cria entradas favoritiveis para menu e submenu", () => {
  const entries = flattenMenuItemsForFavorites(menuItems);

  assert.deepEqual(
    entries.map((entry) => [entry.path, entry.label, entry.iconKey]),
    [
      ["/produtos", "Listar Produtos", "package"],
      ["/produtos/balanco", "Balanco", "clipboard-list"],
      ["/pdv", "PDV (Vendas)", "shopping-cart"],
    ],
  );
});

test("buildVisibleMenuFavorites mostra apenas favoritos permitidos pelo menu atual", () => {
  const visible = buildVisibleMenuFavorites(
    [
      { path: "/pdv", label: "PDV antigo", icon_key: "shopping-cart" },
      { path: "/financeiro", label: "Financeiro", icon_key: "trending-up" },
      { path: "/produtos/balanco", label: "Balanco", iconKey: "clipboard-list" },
    ],
    menuItems,
  );

  assert.deepEqual(
    visible.map((entry) => [entry.path, entry.label, entry.iconKey]),
    [
      ["/pdv", "PDV (Vendas)", "shopping-cart"],
      ["/produtos/balanco", "Balanco", "clipboard-list"],
    ],
  );
});

test("toggleMenuFavorite adiciona e remove favoritos preservando ordem", () => {
  const pdv = { path: "/pdv", label: "PDV (Vendas)", iconKey: "shopping-cart" };
  const produtos = { path: "/produtos", label: "Listar Produtos", iconKey: "package" };

  const comPdv = toggleMenuFavorite([], pdv);
  const comDois = toggleMenuFavorite(comPdv, produtos);
  const semPdv = toggleMenuFavorite(comDois, pdv);

  assert.deepEqual(comPdv, [{ path: "/pdv", label: "PDV (Vendas)", icon_key: "shopping-cart" }]);
  assert.deepEqual(
    comDois.map((entry) => entry.path),
    ["/pdv", "/produtos"],
  );
  assert.deepEqual(semPdv, [{ path: "/produtos", label: "Listar Produtos", icon_key: "package" }]);
});

test("toggleMenuFavorite bloqueia inclusao acima do limite", () => {
  const favoritos = Array.from({ length: MAX_MENU_FAVORITES }, (_, index) => ({
    path: `/atalho-${index}`,
    label: `Atalho ${index}`,
    icon_key: "star",
  }));

  assert.throws(
    () =>
      toggleMenuFavorite(favoritos, {
        path: "/novo",
        label: "Novo",
        iconKey: "star",
      }),
    /maximo 8 favoritos/i,
  );
});

test("reorderMenuFavorites reordena favoritos existentes pelo caminho", () => {
  const favoritos = [
    { path: "/pdv", label: "PDV (Vendas)", icon_key: "shopping-cart" },
    { path: "/produtos", label: "Listar Produtos", icon_key: "package" },
    { path: "/produtos/balanco", label: "Balanco", icon_key: "clipboard-list" },
  ];

  assert.deepEqual(
    reorderMenuFavorites(favoritos, "/produtos", "/pdv").map((entry) => entry.path),
    ["/produtos", "/pdv", "/produtos/balanco"],
  );
});

test("reorderMenuFavorites preserva ordem quando o alvo nao existe", () => {
  const favoritos = [
    { path: "/pdv", label: "PDV (Vendas)", icon_key: "shopping-cart" },
    { path: "/produtos", label: "Listar Produtos", icon_key: "package" },
  ];

  assert.deepEqual(
    reorderMenuFavorites(favoritos, "/produtos", "/financeiro").map((entry) => entry.path),
    ["/pdv", "/produtos"],
  );
});

test("shouldBlockFavoriteShortcutClick bloqueia clique durante ou logo apos arraste", () => {
  assert.equal(shouldBlockFavoriteShortcutClick({ isDragging: true, now: 1000 }), true);
  assert.equal(shouldBlockFavoriteShortcutClick({ suppressClickUntil: 1300, now: 1200 }), true);
  assert.equal(shouldBlockFavoriteShortcutClick({ suppressClickUntil: 1300, now: 1400 }), false);
});

test("normalizeMenuFavorites limpa dados de API e remove duplicados", () => {
  assert.deepEqual(
    normalizeMenuFavorites([
      { path: " /pdv ", label: " PDV ", icon_key: " shopping-cart " },
      { path: "/pdv", label: "Duplicado", icon_key: "x" },
      { path: "", label: "Sem caminho", icon_key: "x" },
      null,
    ]),
    [{ path: "/pdv", label: "PDV", icon_key: "shopping-cart" }],
  );
});
