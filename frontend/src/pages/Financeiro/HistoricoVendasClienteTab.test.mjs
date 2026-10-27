import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const recebimento = {
  tipo: "recebimento",
  data: "2026-10-26T00:00:00",
  status: "efetivado",
  valor: 209.9,
  descricao: "Recebimento da venda importada",
  detalhes: {
    recebimento_id: 12595,
    conta_receber_id: 11119,
    venda_id: 1340080,
    data_baixa: "2026-10-26",
    registrado_em: "2026-10-27T01:30:00Z",
    forma_pagamento: "pix",
    observacoes: "Cliente pagou dia 28/09.\nObservação original completa.",
  },
};
const pagina = (historico = [recebimento], atual = 1) => ({
  data: {
    historico,
    resumo: { total_vendas_90d: 1234.5, total_em_aberto: 100 },
    paginacao: {
      pagina_atual: atual,
      total_paginas: 2,
      itens_por_pagina: 20,
      total_itens: 21,
      tem_anterior: atual > 1,
      tem_proxima: atual < 2,
    },
  },
});

function preparar(get) {
  const padrao = (name) => ({ __esModule: true, default: name });
  const mocks = new Map([
    ["react-icons/fi", {}],
    ["react-router-dom", { useNavigate: () => () => {} }],
    ["../../api", { __esModule: true, default: { get } }],
    ["../../components/TutorAutocomplete", padrao("TutorAutocomplete")],
    ["../../components/ui/ProductIdentity", padrao("ProductIdentity")],
    ["../../components/ui/SaleReference", padrao("SaleReference")],
    ["../clienteFinanceiro/ClienteFinanceiroView", { DetalhesTransacao: "DetalhesTransacao" }],
    ...["BotaoCancelar", "BotaoInteracao", "InputData", "InputCombobox"].map((name) => [
      `../../components/v2/${name}/${name}`,
      padrao(name),
    ]),
  ]);
  return createControllerHarness(
    fileURLToPath(new URL("./HistoricoVendasClienteTab.jsx", import.meta.url)),
    {
      mocks,
      exportName: "HistoricoInline",
      props: { clienteId: 47644, clienteInfo: { nome: "Cliente QA", codigo: "1848" } },
    },
  );
}

test("aba lê recebimentos e reutiliza detalhes por campo, data local e situação financeira", async () => {
  const chamadas = [];
  const app = preparar(async (url) => {
    chamadas.push(url);
    return pagina([
      recebimento,
      {
        tipo: "venda",
        data: "2026-10-26",
        status: "finalizada",
        status_pagamento: "pago",
        valor: 100,
        detalhes: {},
      },
      { ...recebimento, status: "estornado", valor: -50, descricao: "Estorno do recebimento" },
    ]);
  });
  assert.match(elementText(app.tree), /Carregando histórico/);
  await app.settle();
  const texto = elementText(app.tree);
  assert.match(texto, /26-10-2026/);
  assert.match(texto, /Recebido/);
  assert.match(texto, /Pago/);
  assert.match(texto, /Estornado/);
  assert.match(texto, /R\$ 1\.234,50/);
  assert.doesNotMatch(texto, /efetivado|finalizada|2026-10-26T/);
  assert.ok(
    !elements(app.tree).some((node) =>
      ["input", "select", "button", "textarea"].includes(node.type),
    ),
  );
  const expandir = elements(app.tree).find((node) => node.props?.["aria-label"] === "Ver detalhes");
  await app.act(() => expandir.props.onClick());
  const detalhes = elements(app.tree).find((node) => node.type === "DetalhesTransacao");
  assert.deepEqual(detalhes.props.transacao, recebimento);
  assert.equal(chamadas.length, 1); // Expandir recibo usa os dados da página, sem escrita.
  assert.equal(new URL(chamadas[0], "http://dev").pathname, "/financeiro/cliente/47644");
});

test("filtros V2 são enviados no GET e reiniciam a paginação", async () => {
  const chamadas = [];
  const app = preparar(async (url) => {
    const params = Object.fromEntries(new URL(url, "http://dev").searchParams);
    chamadas.push(params);
    return pagina([recebimento], Number(params.page));
  });
  await app.settle();
  await app.act(() =>
    elements(app.tree)
      .find((node) => node.type === "BotaoInteracao" && elementText(node) === "Próxima")
      .props.onClick(),
  );
  assert.equal(chamadas.at(-1).page, "2");
  const situacao = elements(app.tree).find(
    (node) => node.type === "InputCombobox" && node.props.label === "Situação",
  );
  assert.ok(
    situacao.props.opcoes.some(
      (opcao) => opcao.value === "recebido" && opcao.label === "Pago / recebido",
    ),
  );
  await app.act(() => situacao.props.onChange("recebido"));
  assert.equal(chamadas.at(-1).page, "1");
  assert.equal(chamadas.at(-1).status, "recebido");
  const tipo = elements(app.tree).find(
    (node) => node.type === "InputCombobox" && node.props.label === "Tipo",
  );
  assert.deepEqual(
    tipo.props.opcoes.map((opcao) => opcao.value),
    ["", "venda", "devolucao", "conta_receber", "recebimento", "credito"],
  );
  await app.act(() => tipo.props.onChange("recebimento"));
  const data = elements(app.tree).find(
    (node) => node.type === "InputData" && node.props.label === "Data inicial",
  );
  await app.act(() => data.props.onChange("2026-10-01"));
  assert.deepEqual(chamadas.at(-1), {
    page: "1",
    per_page: "20",
    data_inicio: "2026-10-01",
    tipo: "recebimento",
    status: "recebido",
  });
});

test("resposta do cliente anterior não encerra o loading nem substitui o histórico novo", async () => {
  const pendentes = [];
  const app = preparar((url) => new Promise((resolve) => pendentes.push({ url, resolve })));
  await app.update({ clienteId: 9, clienteInfo: { nome: "Outro cliente", codigo: "9" } });
  assert.equal(pendentes.length, 2);
  pendentes[0].resolve(pagina([{ ...recebimento, descricao: "Movimento do cliente anterior" }]));
  await app.settle();
  assert.match(elementText(app.tree), /Carregando histórico/);
  assert.doesNotMatch(elementText(app.tree), /Movimento do cliente anterior/);
  pendentes[1].resolve(pagina([{ ...recebimento, descricao: "Movimento do cliente atual" }]));
  await app.settle();
  assert.match(elementText(app.tree), /Movimento do cliente atual/);
  assert.doesNotMatch(elementText(app.tree), /Movimento do cliente anterior|Carregando histórico/);
  app.unmount();
});

test("falha do GET permanece explícita e retry somente consulta novamente", async () => {
  let chamadas = 0;
  const app = preparar(async () => {
    chamadas += 1;
    if (chamadas === 1) throw new Error("timeout");
    return pagina();
  });
  await app.settle();
  assert.match(elementText(app.tree), /Erro ao carregar histórico financeiro/);
  await app.act(() =>
    elements(app.tree)
      .find((node) => node.type === "BotaoInteracao" && elementText(node) === "Tentar novamente")
      .props.onClick(),
  );
  assert.equal(chamadas, 2);
  assert.doesNotMatch(elementText(app.tree), /Erro ao carregar histórico financeiro/);
});
