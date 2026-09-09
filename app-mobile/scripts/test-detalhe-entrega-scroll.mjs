import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { runInNewContext } from "node:vm";
import { test } from "node:test";
import ts from "typescript";

// Testa a composicao e os callbacks reais, sem fingir executar gestos nativos.
// A rolagem por toque ainda precisa ser validada no Android/iOS.
const require = createRequire(import.meta.url);
const React = require("react");
const screenDir = resolve(import.meta.dirname, "../src/screens/entregador/detalhe");
const native = Object.fromEntries(
  ["View", "Text", "TouchableOpacity", "ActivityIndicator", "FlatList"].map(
    (name) => [name, name],
  ),
);
native.StyleSheet = { create: (styles) => styles };

function loadScreen(file, dependencies = {}, extension = "tsx") {
  const filename = resolve(screenDir, `${file}.${extension}`);
  const source = readFileSync(filename, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.React,
      esModuleInterop: true,
    },
  }).outputText;
  const module = { exports: {} };
  runInNewContext(output, {
    module,
    exports: module.exports,
    require: (name) => {
      if (name === "react") return React;
      if (name === "react-native") return native;
      if (Object.hasOwn(dependencies, name)) return dependencies[name];
      throw new Error(`Dependencia nao declarada: ${name}`);
    },
  }, { filename });
  return module.exports;
}

const styles = new Proxy({}, { get: (_, name) => ({ name }) });
const shared = {
  "./DetalheEntregaStyles": { detalheEntregaStyles: styles },
  "./DetalheEntregaUtils": loadScreen("DetalheEntregaUtils", {
    "expo-location": {},
    "@/utils/mapsAddress": {},
  }, "ts"),
};
const { DetalheEntregaStopCard } = loadScreen("DetalheEntregaStopCard", shared);
const { DetalheEntregaContent } = loadScreen("DetalheEntregaContent", {
  ...shared,
  "react-native-draggable-flatlist": "DraggableFlatList",
  "./DetalheEntregaStopCard": { DetalheEntregaStopCard },
  "./DetalheEntregaModals": { DetalheEntregaModals: "Modals" },
});

function elements(node) {
  if (Array.isArray(node)) return node.flatMap(elements);
  if (!React.isValidElement(node)) return [];
  return [node, ...elements(node.props.children)];
}

function texts(node) {
  if (Array.isArray(node)) return node.flatMap(texts);
  if (React.isValidElement(node)) return texts(node.props.children);
  return typeof node === "string" || typeof node === "number" ? [String(node)] : [];
}

// Mesmo volume e distribuicao da imagem enviada: 67 paradas, 24 entregues.
const paradas = Array.from({ length: 67 }, (_, index) => ({
  id: index + 1,
  venda_id: index + 1001,
  ordem: index + 1,
  cliente_nome: `Cliente Teste Rolagem ${String(index + 1).padStart(2, "0")}`,
  endereco: `Rua Ficticia de Teste, ${index + 1} - Demo`,
  status: index < 24 ? "entregue" : "pendente",
}));

function render(status = "em_rota", overrides = {}) {
  return DetalheEntregaContent({
    loading: false,
    rota: { id: 1, numero: "DEMO-ROLAGEM-67", status, paradas: [...paradas].reverse() },
    processando: null,
    statusRastreamento: "ativo",
    ...overrides,
  });
}

test("67 entregas usam uma lista com rolagem e resumo 67/43/24", () => {
  const tree = render();
  assert.equal(tree.type, "View", "A lista nao deve estar dentro de outro scroller");
  const lists = elements(tree).filter((node) => /FlatList/.test(node.type));
  assert.equal(lists.length, 1);
  const list = lists[0];
  assert.notEqual(list.props.scrollEnabled, false);
  assert.equal(list.props.data.length, 67);
  assert.equal(new Set(list.props.data.map(list.props.keyExtractor)).size, 67);
  assert.deepEqual(texts(list.props.ListHeaderComponent).slice(0, 6), [
    "67", "Total", "43", "Pendentes", "24", "Entregues",
  ]);
  assert.ok(texts(list.props.ListHeaderComponent).includes("Rastreamento ativo"));
  assert.equal(list.props.renderItem({ item: list.props.data[66] }).props.parada.ordem, 67);
  assert.ok(elements(tree).some((node) => node.type === "Modals"));
});

test("reordenacao conserva as 67 entregas e encaminha a nova ordem", () => {
  let saved;
  const list = elements(render("em_rota", {
    salvarNovaOrdemParadas: (data) => { saved = data; },
  })).find((node) => node.type === "DraggableFlatList");
  const reordered = [...list.props.data];
  reordered.unshift(reordered.pop());
  list.props.onDragEnd({ data: reordered, from: 66, to: 0 });
  assert.equal(saved.length, 67);
  assert.equal(saved[0].id, 67);
  assert.equal(new Set(saved.map((item) => item.id)).size, 67);
});

test("rota encerrada continua rolavel e nao oferece arrastar", () => {
  for (const status of ["concluida", "cancelada"]) {
    const nodes = elements(render(status));
    assert.ok(!nodes.some((node) => node.type === "DraggableFlatList"));
    const list = nodes.find((node) => node.type === "FlatList");
    assert.equal(list.props.data.length, 67);
    assert.notEqual(list.props.scrollEnabled, false);
    assert.equal(list.props.renderItem({ item: paradas[66] }).props.drag, undefined);
  }
});

test("somente segurar o icone inicia arrasto; numero abre a ordem manual", () => {
  let dragged = 0;
  let selected;
  const card = DetalheEntregaStopCard({
    parada: paradas[24], rotaStatus: "em_rota", processando: null,
    drag: () => { dragged += 1; },
    abrirModalOrdem: (item) => { selected = item; },
  });
  const nodes = elements(card);
  const handles = nodes.filter((node) => node.props.onLongPress);
  assert.equal(handles.length, 1);
  assert.equal(handles[0].props.onPress, undefined);
  assert.ok(handles[0].props.delayLongPress >= 250);
  handles[0].props.onLongPress();
  assert.equal(dragged, 1);
  nodes.find((node) => node.type === "TouchableOpacity" && texts(node).includes("25")).props.onPress();
  assert.equal(selected.id, 25);
});
