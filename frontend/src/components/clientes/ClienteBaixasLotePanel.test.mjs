import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const componentPath = fileURLToPath(new URL("./ClienteBaixasLotePanel.jsx", import.meta.url));
const lote = {
  id: 7,
  data: "2026-10-19T12:00:00-03:00",
  valor_total: 120,
  forma_pagamento: "pix",
  usuario_nome: "Operador",
  status: "confirmado",
  vendas: [
    { venda_id: 11, numero_venda: "VEN-11", valor_baixado: 50 },
    { venda_id: 12, numero_venda: "VEN-12", valor_baixado: 70 },
  ],
};

function preparar({ get, post, onAtualizado } = {}) {
  const chamadas = [];
  const avisos = [];
  const api = {
    get: async (url, options) => {
      chamadas.push({ method: "get", url, options });
      return get ? get(url, options) : { data: { itens: [lote], total: 1, page: 1, per_page: 10 } };
    },
    post: async (url, payload) => {
      chamadas.push({ method: "post", url, payload });
      return post ? post(url, payload) : { data: { ...lote, status: "estornado" } };
    },
  };
  const componentes = [
    "BotaoCancelar",
    "BotaoInteracao",
    "EstadoVazio",
    "InputTextoLongo",
    "ModalPadrao",
  ];
  const mocks = new Map([
    ["../../api", api],
    [
      "lucide-react",
      Object.fromEntries(
        ["ChevronDown", "ChevronLeft", "ChevronRight", "ChevronUp", "History", "RotateCcw"].map(
          (name) => [name, name],
        ),
      ),
    ],
    [
      "react-hot-toast",
      {
        toast: {
          success: (message) => avisos.push(message),
          error: (message) => avisos.push(message),
        },
      },
    ],
    ...componentes.map((name) => [`../v2/${name}/${name}`, { __esModule: true, default: name }]),
  ]);
  const harness = createControllerHarness(componentPath, {
    mocks,
    props: { clienteId: 5, onAtualizado },
  });
  return { harness, chamadas, avisos };
}

function botao(harness, text) {
  const match = elements(harness.tree).find(
    (node) => node.type === "BotaoInteracao" && elementText(node).trim() === text,
  );
  assert.ok(match, `Botão ${text} encontrado`);
  return match;
}

function confirmacao(harness) {
  const modal = elements(harness.tree).find((node) => node.type === "ModalPadrao");
  assert.ok(modal);
  const button = elements(modal.props.rodape).find((node) => node.type === "BotaoInteracao");
  return button;
}

test("mostra um lançamento por lote e detalha o rateio sem repetir o total", async () => {
  const { harness, chamadas } = preparar();
  assert.match(elementText(harness.tree), /Carregando baixas em lote/);
  await harness.settle();
  assert.deepEqual(chamadas[0], {
    method: "get",
    url: "/clientes/5/baixas-lote",
    options: { params: { page: 1, per_page: 10 } },
  });
  assert.equal(elements(harness.tree).filter((node) => node.type === "tbody").length, 1);
  await harness.act(() => botao(harness, "Detalhes").props.onClick());
  assert.match(elementText(harness.tree), /VEN-11/);
  assert.match(elementText(harness.tree), /VEN-12/);
  assert.match(elementText(harness.tree), /R\$ 120,00/);
});

test("motivo obrigatório impede envio e sucesso atualiza lista e pai", async () => {
  let atualizacoes = 0;
  const { harness, chamadas, avisos } = preparar({
    onAtualizado: () => {
      atualizacoes += 1;
    },
  });
  await harness.settle();
  await harness.act(() => botao(harness, "Estornar").props.onClick());
  await harness.act(() => confirmacao(harness).props.onClick());
  assert.equal(chamadas.filter((call) => call.method === "post").length, 0);
  assert.match(elementText(harness.tree), /pelo menos 5 caracteres/);
  await harness.act(() =>
    elements(harness.tree)
      .find((node) => node.type === "InputTextoLongo")
      .props.onChange("  Forma de pagamento errada  "),
  );
  await harness.act(() => confirmacao(harness).props.onClick());
  assert.deepEqual(
    chamadas.find((call) => call.method === "post"),
    {
      method: "post",
      url: "/clientes/5/baixas-lote/7/estornar",
      payload: { motivo: "Forma de pagamento errada" },
    },
  );
  assert.equal(atualizacoes, 1);
  assert.equal(chamadas.filter((call) => call.method === "get").length, 2);
  assert.equal(avisos.length, 1);
  assert.equal(
    elements(harness.tree).some((node) => node.type === "ModalPadrao"),
    false,
  );
});

test("bloqueio do backend mantém motivo e confirmação sem anunciar sucesso", async () => {
  const { harness, avisos } = preparar({
    post: async () => {
      throw { response: { data: { detail: "Abra um caixa antes de estornar." } } };
    },
  });
  await harness.settle();
  await harness.act(() => botao(harness, "Estornar").props.onClick());
  await harness.act(() =>
    elements(harness.tree)
      .find((node) => node.type === "InputTextoLongo")
      .props.onChange("Baixa indevida"),
  );
  await harness.act(() => confirmacao(harness).props.onClick());
  assert.match(elementText(harness.tree), /Abra um caixa antes de estornar/);
  assert.equal(
    elements(harness.tree).find((node) => node.type === "InputTextoLongo").props.value,
    "Baixa indevida",
  );
  assert.deepEqual(avisos, []);
});

test("cliques repetidos durante requisição enviam um único estorno", async () => {
  let concluir;
  const pendente = new Promise((resolve) => {
    concluir = resolve;
  });
  const { harness, chamadas } = preparar({ post: () => pendente });
  await harness.settle();
  await harness.act(() => botao(harness, "Estornar").props.onClick());
  await harness.act(() =>
    elements(harness.tree)
      .find((node) => node.type === "InputTextoLongo")
      .props.onChange("Baixa indevida"),
  );
  const handler = confirmacao(harness).props.onClick;
  const envio = handler();
  await handler();
  assert.equal(chamadas.filter((call) => call.method === "post").length, 1);
  concluir({ data: {} });
  await envio;
  await harness.settle();
});

test("lote estornado continua visível com motivo e sem nova ação de estorno", async () => {
  const { harness } = preparar({
    get: async () => ({
      data: {
        itens: [
          {
            ...lote,
            status: "estornado",
            estornado_em: lote.data,
            motivo_estorno: "Baixa indevida",
            estornado_por_nome: "Gestor",
          },
        ],
        total: 1,
      },
    }),
  });
  await harness.settle();
  assert.equal(
    elements(harness.tree).some(
      (node) => node.type === "BotaoInteracao" && elementText(node) === "Estornar",
    ),
    false,
  );
  await harness.act(() => botao(harness, "Detalhes").props.onClick());
  assert.match(elementText(harness.tree), /Baixa indevida/);
  assert.match(elementText(harness.tree), /Gestor/);
});
