import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as fiscalStatus from "../../utils/pdvFiscalStatus.js";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

function montarBanner(vendaAtual, props = {}) {
  const componentes = [
    ["../ImprimirCupom", "ImprimirCupom"],
    ["../ui/ActionButton", "ActionButton"],
    ["../v2/BotaoInteracao/BotaoInteracao", "BotaoInteracao"],
    ["./ImprimirDocumentoFiscalButton", "ImprimirDocumentoFiscalButton"],
    ["./ModalSelecaoDocumentoFiscal", "ModalSelecaoDocumentoFiscal"],
    ["./ModalDadosVendaFinalizada", "ModalDadosVendaFinalizada"],
  ];
  return createControllerHarness(
    fileURLToPath(new URL("./PDVModoVisualizacaoBanner.jsx", import.meta.url)),
    {
      mocks: new Map([
        ...componentes.map(([path, name]) => [path, { __esModule: true, default: name }]),
        [
          "lucide-react",
          Object.fromEntries(
            ["AlertCircle", "FileText", "Pencil", "RotateCcw", "Trash2", "X"].map((name) => [
              name,
              name,
            ]),
          ),
        ],
        ["../../contexts/ModulosContext", { useModulos: () => ({ moduloAtivo: () => false }) }],
        ["../../utils/caixaAbertoMonitor", { mensagemCaixaIndisponivel: () => "Caixa fechado" }],
        ["../../utils/pdvFiscalStatus", fiscalStatus],
      ]),
      props: { ativo: true, vendaAtual, ...props },
    },
  );
}

function botaoCancelar(harness) {
  return elements(harness.tree).find(
    (node) => node.type === "BotaoInteracao" && elementText(node) === "Cancelar venda",
  );
}

test("pedido iFood mantém itens e valores em visualizacao e permite cancelamento", () => {
  const harness = montarBanner({ id: 42, canal: "ifood", status: "aberta", tem_entrega: true });
  assert.match(elementText(harness.tree), /Itens e valores vêm do pedido iFood/);
  assert.ok(botaoCancelar(harness));
  for (const label of ["Editar", "Reabrir Venda", "Devolucao"]) {
    assert.equal(
      elements(harness.tree).some((node) => elementText(node) === label),
      false,
    );
  }
});

test("app e ecommerce preservam a acao de editar vendas abertas", () => {
  for (const canal of ["app", "ecommerce"]) {
    const harness = montarBanner({ id: 42, canal, status: "aberta", tem_entrega: true });
    assert.ok(
      elements(harness.tree).find(
        (node) => node.type === "ActionButton" && elementText(node) === "Editar",
      ),
    );
  }
});

test("nota cancelada exibe cancelamento direto, preservando o fluxo de confirmação existente", async () => {
  let cancelamentos = 0;
  const harness = montarBanner(
    { id: 26, status: "pago_nf", nfe_modelo: 65, nfe_status: "cancelada" },
    { onCancelarVenda: () => cancelamentos++ },
  );

  assert.match(elementText(harness.tree), /Venda\s+com NF cancelada/);
  assert.doesNotMatch(elementText(harness.tree), /Venda\s+com NF emitida/);
  assert.equal(botaoCancelar(harness)?.props.icon, "Trash2");
  await harness.act(() => botaoCancelar(harness).props.onClick());
  assert.equal(cancelamentos, 1);

  await harness.update({ loading: true });
  assert.equal(botaoCancelar(harness).props.disabled, true);
});

test("venda ativa permite cancelar mesmo com nota autorizada ou em processamento", async () => {
  const vendaAtual = { id: 26, status: "pago_nf", nfe_modelo: 65, nfe_status: "autorizada" };
  const harness = montarBanner(vendaAtual);
  assert.ok(botaoCancelar(harness));

  await harness.update({ vendaAtual: { ...vendaAtual, nfe_status: "processando" } });
  assert.ok(botaoCancelar(harness));

  await harness.update({
    vendaAtual: { ...vendaAtual, status: "finalizada", nfe_status: "cancelada" },
  });
  assert.ok(botaoCancelar(harness));
  assert.match(elementText(harness.tree), /Venda\s+com NF cancelada/);

  await harness.update({
    vendaAtual: { ...vendaAtual, status: "cancelada", nfe_status: "cancelada" },
  });
  assert.equal(botaoCancelar(harness), undefined);
  assert.match(elementText(harness.tree), /Venda\s+Cancelada/);
  assert.doesNotMatch(elementText(harness.tree), /Reabra a venda para modificar/);

  await harness.update({
    vendaAtual: { ...vendaAtual, status: "finalizada_devolucao", nfe_status: "cancelada" },
  });
  assert.equal(botaoCancelar(harness), undefined);
});
