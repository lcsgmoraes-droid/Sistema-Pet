import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const criarNota = (id = 11) => ({
  id,
  status: "pendente",
  itens: [
    {
      id: 101,
      produto_id: 501,
      quantidade: 18,
      valor_unitario: 2.59,
      valor_total: 46.62,
      pack_multiplicador_detectado: 18,
    },
  ],
});

function preparar({ notaSelecionada = criarNota(), autorizada = false } = {}) {
  const eventos = [];
  const mensagens = [];
  const nota = criarNota(11);
  const preview = {
    nota_id: nota.id,
    status: nota.status,
    itens: nota.itens.map(({ id, quantidade, valor_unitario, valor_total, ...item }) => ({
      ...item,
      item_id: id,
      quantidade_nf: quantidade,
      valor_unitario_nf: valor_unitario,
      valor_total_nf: valor_total,
      custo_aquisicao_total_nf: valor_total,
    })),
  };
  const controle = { autorizada };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useEntradaXmlRevisaoPrecos.js", import.meta.url)),
    {
      mocks: new Map([
        ["../../utils/formatters", { formatBRL: (valor) => String(valor) }],
        [
          "./entradaXmlRelatorioCustos",
          {
            exportarRelatorioCustosMaioresCSV() {},
            exportarRelatorioCustosMaioresPDF() {},
          },
        ],
      ]),
      props: {
        api: {
          async get(url) {
            eventos.push(["get", url]);
            if (url.endsWith("/preview-processamento")) return { data: preview };
            return { data: nota };
          },
          async post(url, payload) {
            eventos.push(["post", url, payload]);
            return { data: { message: "Processado", precos_venda_atualizados: 0 } };
          },
        },
        carregarDados: () => eventos.push(["carregarDados"]),
        multiplicadoresPack: {},
        notaSelecionada,
        salvarConferenciaAtual: async () => {
          eventos.push(["salvarConferencia"]);
          return true;
        },
        validarPackAntesDeProcessar: (notaValidada) => {
          eventos.push(["validarPack", notaValidada]);
          return controle.autorizada;
        },
        setLoading: (valor) => eventos.push(["loading", valor]),
        setMostrarDetalhes: (valor) => eventos.push(["detalhes", valor]),
        setMostrarVisualizacao: (valor) => eventos.push(["visualizacao", valor]),
        setNotaSelecionada: (valor) => eventos.push(["notaSelecionada", valor]),
        toast: {
          error: (mensagem) => mensagens.push(mensagem),
          success: (mensagem) => mensagens.push(mensagem),
        },
      },
    },
  );
  return { harness, eventos, mensagens, controle, nota, preview };
}

test("pack sem OK impede salvar conferência e abrir a revisão", async () => {
  const { harness, eventos } = preparar();
  await harness.act(() => harness.tree.carregarPreviewProcessamento(11));

  assert.ok(eventos.some(([acao]) => acao === "validarPack"));
  assert.equal(
    eventos.some(([acao]) => acao === "salvarConferencia"),
    false,
  );
  assert.equal(
    eventos.some(([acao, url]) => acao === "get" && url.endsWith("/preview-processamento")),
    false,
  );
  assert.equal(harness.tree.mostrarRevisaoPrecos, false);
});

test("atalho para outra nota consulta seus dados e também bloqueia o preview sem OK", async () => {
  const { harness, eventos } = preparar({ notaSelecionada: criarNota(99) });
  await harness.act(() => harness.tree.carregarPreviewProcessamento(11));

  assert.ok(eventos.some(([acao, url]) => acao === "get" && url === "/notas-entrada/11"));
  const validacao = eventos.find(([acao]) => acao === "validarPack");
  assert.equal(validacao[1].id, 11);
  assert.equal(
    eventos.some(([acao]) => acao === "salvarConferencia"),
    false,
  );
  assert.equal(
    eventos.some(([acao, url]) => acao === "get" && url.endsWith("/preview-processamento")),
    false,
  );
  assert.equal(harness.tree.mostrarRevisaoPrecos, false);
});

test("com os OKs válidos a revisão abre depois da validação e da conferência", async () => {
  const { harness, eventos } = preparar({ autorizada: true });
  await harness.act(() => harness.tree.carregarPreviewProcessamento(11));

  const validar = eventos.findIndex(([acao]) => acao === "validarPack");
  const salvar = eventos.findIndex(([acao]) => acao === "salvarConferencia");
  const carregar = eventos.findIndex(
    ([acao, url]) => acao === "get" && url.endsWith("/preview-processamento"),
  );
  assert.ok(validar >= 0 && salvar > validar && carregar > salvar);
  assert.equal(harness.tree.mostrarRevisaoPrecos, true);
  assert.equal(harness.tree.previewProcessamento.nota_id, 11);
});

test("retirar a confirmação depois do preview impede o POST final", async () => {
  const { harness, eventos, controle } = preparar({ autorizada: true });
  await harness.act(() => harness.tree.carregarPreviewProcessamento(11));
  eventos.length = 0;
  controle.autorizada = false;

  await harness.act(() => harness.tree.confirmarProcessamento());

  assert.ok(eventos.some(([acao]) => acao === "validarPack"));
  assert.equal(
    eventos.some(([acao]) => acao === "post"),
    false,
  );
});

test("a confirmação final válida mantém o processamento da nota", async () => {
  const { harness, eventos } = preparar({ autorizada: true });
  await harness.act(() => harness.tree.carregarPreviewProcessamento(11));
  eventos.length = 0;
  await harness.act(() => harness.tree.confirmarProcessamento());

  const validar = eventos.findIndex(([acao]) => acao === "validarPack");
  const postar = eventos.findIndex(
    ([acao, url]) => acao === "post" && url === "/notas-entrada/11/processar",
  );
  assert.ok(validar >= 0 && postar > validar);
  assert.equal(harness.tree.mostrarRevisaoPrecos, false);
  assert.equal(harness.tree.previewProcessamento, null);
});
