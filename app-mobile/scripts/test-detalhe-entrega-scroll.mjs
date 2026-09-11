import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";
import React from "react";
import ts from "typescript";

// Testa a composicao e os callbacks reais, sem fingir executar gestos nativos.
// A rolagem por toque ainda precisa ser validada no Android/iOS.
const screenDir = resolve(import.meta.dirname, "../src/screens/entregador/detalhe");
const nativeMocks = {
  "react-native": `
    export const View = 'View', Text = 'Text', TouchableOpacity = 'TouchableOpacity';
    export const ActivityIndicator = 'ActivityIndicator', FlatList = 'FlatList';
    export const StyleSheet = {create: styles => styles};
    export const Alert = {}, Linking = {};
  `,
  "react-native-draggable-flatlist": "export default 'DraggableFlatList';",
  "expo-location": "export {};",
  "@/utils/format": `
    export const formatarMoeda = value => 'R$ ' + Number(value || 0).toFixed(2).replace('.', ',');
  `,
  "@/utils/mapsAddress": "export const limparEnderecoParaMaps = value => value;",
  "./DetalheEntregaModals": "export const DetalheEntregaModals = 'Modals';",
};
const screenFiles = new Map([
  ["./DetalheEntregaContent", "DetalheEntregaContent.tsx"],
  ["./DetalheEntregaStopCard", "DetalheEntregaStopCard.tsx"],
  ["./DetalheEntregaStyles", "DetalheEntregaStyles.ts"],
  ["./DetalheEntregaUtils", "DetalheEntregaUtils.ts"],
].map(([specifier, file]) => [specifier, pathToFileURL(resolve(screenDir, file)).href]));
const sourceUrls = new Set(screenFiles.values());

// O carregador transforma apenas estes quatro arquivos locais conhecidos.
// Usa o importador do Node, com componentes nativos substituidos durante o teste.
const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    if (Object.hasOwn(nativeMocks, specifier)) {
      return {url: `corepet-test:${specifier}`, shortCircuit: true};
    }
    if (sourceUrls.has(context.parentURL) && screenFiles.has(specifier)) {
      return {url: screenFiles.get(specifier), shortCircuit: true};
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url.startsWith("corepet-test:")) {
      return {format: "module", source: nativeMocks[url.slice("corepet-test:".length)], shortCircuit: true};
    }
    if (sourceUrls.has(url)) {
      const {outputText} = ts.transpileModule(readFileSync(fileURLToPath(url), "utf8"), {
        compilerOptions: {module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.React},
      });
      return {format: "module", source: outputText, shortCircuit: true};
    }
    return nextLoad(url, context);
  },
});
let DetalheEntregaContent;
let DetalheEntregaStopCard;
let montarInstrucoesPagamentoEntrega;
try {
  ({DetalheEntregaContent} = await import(screenFiles.get("./DetalheEntregaContent")));
  ({DetalheEntregaStopCard} = await import(screenFiles.get("./DetalheEntregaStopCard")));
  ({montarInstrucoesPagamentoEntrega} = await import(screenFiles.get("./DetalheEntregaUtils")));
} finally {
  hooks.deregister();
}

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

test("pagamento em dinheiro destaca troco e valor levado pelo cliente", () => {
  const instrucoes = montarInstrucoesPagamentoEntrega({
    valor_venda: 45,
    pagamentos: [
      {
        forma_pagamento: "Dinheiro",
        valor: 45,
        valor_recebido: 50,
        troco: 5,
      },
    ],
  });

  assert.equal(instrucoes[0].resumo, "💵 DINHEIRO — R$ 45,00");
  assert.equal(instrucoes[0].alerta, "LEVAR TROCO: R$ 5,00");
  assert.equal(instrucoes[0].complemento, "Cliente paga com R$ 50,00");

  const card = DetalheEntregaStopCard({
    parada: { ...paradas[24], pagamentos: [{ forma_pagamento: "Dinheiro", valor: 45, valor_recebido: 50, troco: 5 }] },
    rotaStatus: "em_rota",
    processando: null,
  });
  const conteudo = texts(card).join(" ");
  assert.match(conteudo, /FORMA DE PAGAMENTO/);
  assert.match(conteudo, /LEVAR TROCO: R\$ 5,00/);
});

test("pagamento em cartao avisa o entregador para levar a maquina", () => {
  const [instrucao] = montarInstrucoesPagamentoEntrega({
    pagamentos: [
      {
        forma_pagamento: "Cartão de crédito",
        modalidade_cartao: "credito",
        numero_parcelas: 3,
        valor: 390,
      },
    ],
  });

  assert.equal(instrucao.resumo, "💳 CARTÃO DE CRÉDITO (3x) — R$ 390,00");
  assert.equal(instrucao.alerta, "LEVAR MÁQUINA DE CARTÃO");
});

test("pagamento ausente gera alerta para confirmar com a loja", () => {
  const [instrucao] = montarInstrucoesPagamentoEntrega({ valor_venda: 45 });

  assert.equal(instrucao.resumo, "⚠️ FORMA NÃO INFORMADA");
  assert.equal(instrucao.alerta, "CONFIRME O PAGAMENTO COM A LOJA");
});
