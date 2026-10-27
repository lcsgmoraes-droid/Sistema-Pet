import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const componentPath = fileURLToPath(new URL("../ContasReceber.jsx", import.meta.url));
const contas = [
  {
    id: 101,
    descricao: "Crediário parcela 1",
    cliente_nome: "Ana",
    valor_original: 100,
    valor_final: 100,
    valor_recebido: 0,
    saldo_atualizado: 100,
    status: "pendente",
    eh_crediario: true,
    data_vencimento: "2026-11-10",
  },
  {
    id: 202,
    descricao: "Crediário parcela 2",
    cliente_nome: "Bruno",
    valor_original: 75,
    valor_final: 75,
    valor_recebido: 0,
    saldo_atualizado: 75,
    status: "pendente",
    eh_crediario: true,
    data_vencimento: "2026-11-11",
  },
];
const recebimento = {
  id: 501,
  valor: 30,
  data: "2026-10-23",
  forma_pagamento_id: 7,
  observacoes: "Pagamento parcial",
};
const padrao = (name) => ({ __esModule: true, default: name });

function preparar({ post, listar, detalhes } = {}) {
  const chamadas = [];
  const avisos = { sucesso: [], erro: [] };
  const api = {
    get: async (url, options) => {
      chamadas.push({ method: "get", url, options });
      if (url.startsWith("/contas-receber/?")) return listar ? listar() : { data: contas };
      if (url === "/clientes/") return { data: [] };
      if (url.startsWith("/financeiro/formas-pagamento"))
        return { data: [{ id: 7, nome: "Pix", tipo: "pix" }] };
      if (url.startsWith("/contas-bancarias"))
        return { data: [{ id: 9, nome: "Conta principal" }] };
      if (url === "/contas-receber/101")
        return {
          data: detalhes || {
            id: 101,
            cliente: { nome: "Ana do histórico" },
            valores: { saldo: 70 },
          },
        };
      throw new Error(`GET inesperado: ${url}`);
    },
    post: async (url, payload) => {
      chamadas.push({ method: "post", url, payload });
      return post ? post(url, payload) : { data: { recebimento, saldo_restante: 70 } };
    },
  };
  const mocks = new Map([
    ["../api", api],
    ["../auth/tokenStorage", { getAccessToken: () => "token-teste" }],
    [
      "react-router-dom",
      { useNavigate: () => () => {}, useSearchParams: () => [new URLSearchParams()] },
    ],
    ["lucide-react", {}],
    [
      "react-hot-toast",
      {
        toast: {
          success: (message) => avisos.sucesso.push(message),
          error: (message) => avisos.erro.push(message),
        },
      },
    ],
    ...[
      "ActionButton",
      "CustomerIdentity",
      "DataTable",
      "LoadingState",
      "PageHeader",
      "StatusBadge",
    ].map((name) => [`./ui/${name}`, padrao(name)]),
    ["./ui/MoneyCell", { ...padrao("MoneyCell"), formatMoneyCellValue: String }],
    ["./ModalNovaContaReceber", padrao("ModalNovaContaReceber")],
    ["./v2/InputCheckbox/InputCheckbox", padrao("InputCheckbox")],
    ["./v2/BotaoInteracao/BotaoInteracao", padrao("BotaoInteracao")],
    ["./v2/BotaoMenuAcoes/BotaoMenuAcoes", padrao("BotaoMenuAcoes")],
    ["./contasReceber/ComprovanteRecebimentoModal", padrao("ComprovanteRecebimentoModal")],
    ["./contasReceber/ContasReceberAnalise", padrao("ContasReceberAnalise")],
    [
      "./contasReceber/ContasReceberPanels",
      Object.fromEntries(
        [
          "ContasReceberDetalhesModal",
          "ContasReceberFilters",
          "ContasReceberRecebimentoLoteModal",
          "ContasReceberRecebimentoModal",
        ].map((name) => [name, name]),
      ),
    ],
  ]);
  const harness = createControllerHarness(componentPath, { mocks });
  return { harness, chamadas, avisos };
}

function componente(harness, type) {
  const match = elements(harness.tree).find((node) => node.type === type);
  assert.ok(match, `${type} visível`);
  return match;
}

function tabela(harness) {
  return componente(harness, "DataTable").props;
}

async function abrirRecebimento(harness) {
  const acoes = tabela(harness)
    .columns.find((column) => column.key === "acoes")
    .render(contas[0]);
  const botao = elements(acoes).find(
    (node) => node.props?.title === "Registrar recebimento manual",
  );
  await harness.act(() => botao.props.onClick());
}

function comprovantes(harness) {
  return componente(harness, "ComprovanteRecebimentoModal").props;
}

function posts(chamadas) {
  return chamadas.filter((call) => call.method === "post");
}

test("recebimento parcial oferece impressão com dados e saldo confirmados pelo servidor", async () => {
  const { harness, chamadas, avisos } = preparar();
  await harness.settle();
  await abrirRecebimento(harness);
  await harness.act(() =>
    componente(harness, "ContasReceberRecebimentoModal").props.setDadosRecebimento((draft) => ({
      ...draft,
      valor_recebido: 30,
      forma_pagamento_id: 7,
      conta_bancaria_id: 9,
      quitar: false,
    })),
  );
  await harness.act(() =>
    componente(harness, "ContasReceberRecebimentoModal").props.registrarRecebimento(),
  );
  assert.equal(posts(chamadas).length, 1);
  assert.equal(posts(chamadas)[0].url, "/contas-receber/101/receber");
  assert.equal(posts(chamadas)[0].payload.quitar, false);
  const modal = comprovantes(harness);
  assert.equal(modal.perguntarImpressao, true);
  assert.equal(modal.comprovantes.length, 1);
  assert.deepEqual(
    Object.fromEntries(
      [
        "id",
        "contaId",
        "clienteNome",
        "valor",
        "saldoRestante",
        "formaPagamento",
        "contaBancaria",
      ].map((key) => [key, modal.comprovantes[0][key]]),
    ),
    {
      id: 501,
      contaId: 101,
      clienteNome: "Ana",
      valor: 30,
      saldoRestante: 70,
      formaPagamento: "Pix",
      contaBancaria: "Conta principal",
    },
  );
  assert.equal(
    componente(harness, "ContasReceberRecebimentoModal").props.mostrarModalRecebimento,
    false,
  );
  assert.equal(avisos.sucesso.length, 1);
  await harness.act(() => modal.onClose());
  assert.deepEqual(comprovantes(harness).comprovantes, []);
  assert.equal(posts(chamadas).length, 1);
});

test("erro no recebimento preserva o formulário e não oferece comprovante", async () => {
  const { harness, chamadas, avisos } = preparar({
    post: async () => {
      throw { response: { data: { detail: "Caixa fechado" } } };
    },
  });
  await harness.settle();
  await abrirRecebimento(harness);
  const quantidadeAntes = chamadas.length;
  await harness.act(() =>
    componente(harness, "ContasReceberRecebimentoModal").props.registrarRecebimento(),
  );
  assert.deepEqual(comprovantes(harness).comprovantes, []);
  assert.equal(
    componente(harness, "ContasReceberRecebimentoModal").props.mostrarModalRecebimento,
    true,
  );
  assert.equal(chamadas.length, quantidadeAntes + 1);
  assert.deepEqual(avisos, { sucesso: [], erro: ["Caixa fechado"] });
});

test("pergunta de impressão permanece disponível enquanto a lista atualiza", async () => {
  let concluirLista;
  let atualizar = false;
  const listaPendente = new Promise((resolve) => {
    concluirLista = resolve;
  });
  const { harness, chamadas } = preparar({
    listar: () => (atualizar ? listaPendente : { data: contas }),
  });
  await harness.settle();
  await abrirRecebimento(harness);
  atualizar = true;
  const envio = componente(harness, "ContasReceberRecebimentoModal").props.registrarRecebimento();
  await harness.settle();
  assert.equal(comprovantes(harness).perguntarImpressao, true);
  assert.equal(comprovantes(harness).comprovantes[0].id, 501);
  await harness.act(() => comprovantes(harness).onClose());
  assert.equal(posts(chamadas).length, 1);
  concluirLista({ data: contas });
  await envio;
  await harness.settle();
  assert.deepEqual(comprovantes(harness).comprovantes, []);
});

async function abrirLote(harness) {
  await harness.act(() =>
    tabela(harness)
      .columns.find((column) => column.key === "selecao")
      .header.props.onChange(),
  );
  const acoes = componente(harness, "PageHeader").props.actions;
  const baixar = elements(acoes).find((node) =>
    elementText(node).startsWith("Baixar selecionadas"),
  );
  await harness.act(() => baixar.props.onClick());
}

test("baixa em lote oferece um comprovante de cada cliente e mantém a identidade de cada conta", async () => {
  const { harness, chamadas } = preparar({
    post: async () => ({
      data: {
        itens: [
          {
            conta_id: 202,
            valor_recebido: 75,
            recebimento: { ...recebimento, id: 502, valor: 75 },
          },
          {
            conta_id: 101,
            valor_recebido: 100,
            recebimento: { ...recebimento, id: 503, valor: 100 },
          },
        ],
      },
    }),
  });
  await harness.settle();
  await abrirLote(harness);
  await harness.act(() =>
    componente(harness, "ContasReceberRecebimentoLoteModal").props.onConfirmar(),
  );
  assert.equal(posts(chamadas).length, 1);
  assert.equal(posts(chamadas)[0].url, "/contas-receber/receber-lote");
  assert.deepEqual([...posts(chamadas)[0].payload.conta_ids].sort(), [101, 202]);
  const modal = comprovantes(harness);
  assert.equal(modal.perguntarImpressao, true);
  assert.equal(modal.comprovantes.length, 2);
  assert.deepEqual(
    [...modal.comprovantes]
      .sort((a, b) => a.contaId - b.contaId)
      .map(({ id, contaId, clienteNome, valor, saldoRestante }) => ({
        id,
        contaId,
        clienteNome,
        valor,
        saldoRestante,
      })),
    [
      { id: 503, contaId: 101, clienteNome: "Ana", valor: 100, saldoRestante: 0 },
      { id: 502, contaId: 202, clienteNome: "Bruno", valor: 75, saldoRestante: 0 },
    ],
  );
  assert.equal(componente(harness, "ContasReceberRecebimentoLoteModal").props.mostrar, false);
  await harness.act(() => modal.onClose());
  assert.equal(posts(chamadas).length, 1);
});

test("erro na baixa em lote mantém seleção e não oferece comprovantes", async () => {
  const { harness, avisos } = preparar({
    post: async () => {
      throw { response: { data: { detail: "Parcela já recebida" } } };
    },
  });
  await harness.settle();
  await abrirLote(harness);
  await harness.act(() =>
    componente(harness, "ContasReceberRecebimentoLoteModal").props.onConfirmar(),
  );
  assert.deepEqual(comprovantes(harness).comprovantes, []);
  assert.equal(componente(harness, "ContasReceberRecebimentoLoteModal").props.mostrar, true);
  assert.equal(
    componente(harness, "ContasReceberRecebimentoLoteModal").props.contasSelecionadas.length,
    2,
  );
  assert.deepEqual(avisos, { sucesso: [], erro: ["Parcela já recebida"] });
});

test("emissão pelo histórico abre o comprovante existente sem lançar outro pagamento", async () => {
  const { harness, chamadas } = preparar();
  await harness.settle();
  const acoes = tabela(harness)
    .columns.find((column) => column.key === "acoes")
    .render(contas[0]);
  await harness.act(() =>
    elements(acoes)
      .find((node) => node.props?.title === "Ver Detalhes")
      .props.onClick(),
  );
  await harness.act(() =>
    componente(harness, "ContasReceberDetalhesModal").props.onEmitirComprovante(recebimento),
  );
  assert.equal(comprovantes(harness).perguntarImpressao, false);
  assert.equal(comprovantes(harness).comprovantes[0].id, 501);
  assert.equal(comprovantes(harness).comprovantes[0].clienteNome, "Ana do histórico");
  assert.equal(comprovantes(harness).comprovantes[0].saldoRestante, 70);
  await harness.act(() => comprovantes(harness).onClose());
  assert.equal(posts(chamadas).length, 0);
});
