import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const caminho = fileURLToPath(new URL("./ClienteFinanceiroView.jsx", import.meta.url));
const padrao = (name) => ({ __esModule: true, default: name });
const mocks = new Map([
  ["react-icons/fi", {}],
  ...[
    "EmptyState",
    "ErrorState",
    "LoadingState",
    "MetricCard",
    "MetricGrid",
    "PageHeader",
    "Panel",
    "ProductIdentity",
    "SaleReference",
  ].map((name) => [`../../components/ui/${name}`, padrao(name)]),
  ["../../components/clientes/ClienteBaixasLotePanel", padrao("ClienteBaixasLotePanel")],
  ...["BotaoInteracao", "InputData", "InputCombobox"].map((name) => [
    `../../components/v2/${name}/${name}`,
    padrao(name),
  ]),
]);
const recebimento = {
  tipo: "recebimento",
  status: "efetivado",
  data: "2026-10-26T00:00:00",
  valor: 209.9,
  descricao: "Recebimento de venda",
  detalhes: {
    recebimento_id: 12595,
    conta_receber_id: 11119,
    venda_id: 1340080,
    data_baixa: "2026-10-26",
    registrado_em: "2026-10-27T01:30:00Z",
    forma_pagamento: "Pix",
    observacoes: "Cliente pagou no dia informado.\nObservação original completa.",
  },
};

test("detalhes mostram referência sem moeda, apenas data da baixa e observação inteira", () => {
  const app = createControllerHarness(caminho, {
    mocks,
    exportName: "DetalhesTransacao",
    props: { transacao: recebimento },
  });
  const texto = elementText(app.tree);
  assert.match(texto, /Recebimento\s+— detalhes/);
  assert.match(texto, /#12595/);
  assert.match(texto, /26-10-2026/);
  assert.ok(texto.includes(recebimento.detalhes.observacoes));
  assert.doesNotMatch(texto, /R\$|Registrado|2026-10-27|1340080/);
  const obs = elements(app.tree).find(
    (item) => item.type === "dd" && elementText(item) === recebimento.detalhes.observacoes,
  );
  assert.match(obs.props.className, /whitespace-pre-wrap/);
});

test("tabela usa situação financeira e filtros V2 com valores controlados", () => {
  const filtrosAplicados = [];
  const app = createControllerHarness(caminho, {
    mocks,
    props: {
      cliente: { id: 1, nome: "Pessoa QA", codigo: "1848" },
      resumo: null,
      detalhesVendas: {},
      expandedRows: {},
      filtros: { tipo: "", status: "", data_inicio: "", data_fim: "", per_page: 20 },
      historico: [
        recebimento,
        {
          tipo: "venda",
          status: "finalizada",
          status_pagamento: "em_aberto",
          data: "2026-10-26",
          valor: 100,
          descricao: "Venda a prazo",
          detalhes: {},
        },
      ],
      loading: false,
      loadingDetalhes: {},
      error: "",
      paginacao: { total_itens: 2, total_paginas: 1 },
      onAplicarFiltros: (filtro) => filtrosAplicados.push(filtro),
    },
  });
  const texto = elementText(app.tree);
  assert.match(texto, /Recebido/);
  assert.match(texto, /Em aberto/);
  assert.match(texto, /26-10-2026/);
  assert.doesNotMatch(texto, /efetivado|finalizada/);
  const nos = elements(app.tree);
  assert.ok(!nos.some((item) => ["input", "select", "button", "textarea"].includes(item.type)));
  nos
    .find((item) => item.type === "InputData" && item.props.label === "Data inicial")
    .props.onChange("2026-10-01");
  const situacao = nos.find(
    (item) => item.type === "InputCombobox" && item.props.label === "Situação",
  );
  assert.ok(
    situacao.props.opcoes.some((opcao) => opcao.value === "vencido" && opcao.label === "Vencido"),
  );
  situacao.props.onChange("parcial");
  assert.deepEqual(filtrosAplicados, [{ data_inicio: "2026-10-01" }, { status: "parcial" }]);
});
