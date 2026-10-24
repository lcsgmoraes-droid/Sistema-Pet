import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const stub = (value) => ({ __esModule: true, default: value });
function setup(status = "matched") {
  const title = {
    id: "title",
    amount: "30.00",
    difference: status === "matched" ? "0.00" : null,
    reconciliation_status: status,
    provider_status: "SUCCEED",
    link_method: status === "matched" ? "legacy_title" : null,
    reference_months: ["2025-08"],
    issues: status === "pending" ? ["Saldo sem relação explícita com título"] : [],
    bank_status: "not_checked",
  };
  const controller = {
    periodo: { inicio: "2025-08-01", fim: "2025-08-03" },
    periodoValido: true,
    basis: "calculation",
    competence: "2025-08",
    mesValido: true,
    relatorio: {
      titles: [title],
      imported: true,
      metadata: { source: "ifood_financial_settlements" },
      summary: { matched_titles: 1, divergent_titles: 0, pending_titles: 0 },
      unmatched_balances: [],
      warnings: [],
    },
    job: { status: "enqueue", competence: "2025-08" },
    seguindo: false,
    tentativas: 0,
  };
  const controls = [
    "BotaoCancelar",
    "BotaoInteracao",
    "CartaoIndicador",
    "EstadoVazio",
    "InputCombobox",
    "InputPeriodo",
    "InputTexto",
    "ModalPadrao",
  ];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodRepasses.jsx", import.meta.url)),
    {
      props: { ativo: true, status: { can_sync_payouts: false } },
      mocks: new Map([
        ...controls.map((name) => [`../v2/${name}/${name}`, stub(name)]),
        ["../ui/DataTable", stub("DataTable")],
        ["lucide-react", { Eye: "Eye", RefreshCw: "RefreshCw" }],
        ["../../utils/modalEscape", { useEscapeToClose() {} }],
        [
          "./ifoodPresentation",
          {
            moedaIfood: (value) =>
              value === null || value === undefined ? "Não informado" : `R$ ${value}`,
          },
        ],
        ["./useIfoodRepasses", stub(() => controller)],
      ]),
    },
  );
  async function detail() {
    const table = elements(harness.tree).find((item) => item.type === "DataTable");
    const action = table.props.columns.find((column) => column.key === "acoes").render(title);
    await harness.act(() => action.props.onClick());
    const modal = elements(harness.tree).find((item) => item.props?.title === title);
    return modal.type(modal.props);
  }
  return { harness, controller, title, detail };
}

test("título conciliado mantém aviso bancário e situação do provedor separada", async () => {
  const env = setup();
  const detail = await env.detail();
  assert.match(elementText(detail), /recebimento no banco não conferido/);
  assert.match(elementText(detail), /SUCCEED/);
  assert.match(elementText(detail), /não comprova crédito/);
  assert.match(elementText(detail), /Não informada pelo iFood/);
  assert.match(elementText(detail), /08\/2025/);
  assert.match(elementText(detail), /Correspondência explícita/);
  assert.match(elementText(detail), /Eventos de toda a apuração \(todos os títulos\)/);
  assert.match(elementText(detail), /Diferença título − linhas vinculadas/);
  assert.match(elementText(detail), /pode incluir outros títulos/);
  const tag = elements(detail).find((item) => item.props?.value === "matched");
  assert.match(elementText(tag.type(tag.props)), /Conciliado no iFood/);
});

test("saldo novo sem relação explícita permanece pendente e valor ausente não vira zero", async () => {
  const env = setup("pending");
  const detail = await env.detail();
  assert.match(elementText(detail), /Saldo sem relação explícita/);
  assert.match(elementText(detail), /Não informado/);
  assert.match(elementText(detail), /ainda precisa ser comprovada/);
  const tag = elements(detail).find((item) => item.props?.value === "pending");
  assert.equal(elementText(tag.type(tag.props)), "Pendente");
});

test("estado de diferença é visível e consulta externa desativada não some com dados importados", async () => {
  const env = setup("different");
  const detail = await env.detail();
  const tag = elements(detail).find((item) => item.props?.value === "different");
  assert.equal(elementText(tag.type(tag.props)), "Com diferença");
  const external = elements(env.harness.tree).find(
    (item) => item.type === "BotaoInteracao" && elementText(item) === "Consultar repasses no iFood",
  );
  assert.equal(external.props.disabled, true);
  assert.ok(elements(env.harness.tree).some((item) => item.type === "DataTable"));
});

test("cartões e estado inicial recebem os ícones obrigatórios dos componentes V2", async () => {
  const env = setup();
  const cards = elements(env.harness.tree).filter((item) => item.type === "CartaoIndicador");
  assert.equal(cards.length, 3);
  assert.ok(cards.every((card) => card.props.icone));
  env.controller.relatorio = null;
  await env.harness.update({ ativo: true });
  const empty = elements(env.harness.tree).find((item) => item.type === "EstadoVazio");
  assert.ok(empty.props.icone);
});
