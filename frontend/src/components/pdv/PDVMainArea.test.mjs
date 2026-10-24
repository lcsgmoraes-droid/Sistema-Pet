import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const children = [
  "PDVAcoesFooterCard",
  "PDVClienteCard",
  "PDVComissaoCard",
  "PDVEntregaCard",
  "PDVHeaderBar",
  "PDVInfoBanners",
  "PDVModoVisualizacaoBanner",
  "PDVObservacoesCard",
  "PDVProdutosCard",
  "PDVResumoFinanceiroCard",
];
function render(vendaAtual) {
  const h = createControllerHarness(fileURLToPath(new URL("./PDVMainArea.jsx", import.meta.url)), {
    props: { vendaAtual: { itens: [], ...vendaAtual }, modoVisualizacao: true },
    mocks: new Map([
      ...children.map((name) => [`./${name}`, { __esModule: true, default: name }]),
      [
        "../ifood/IfoodPdvOnlineVendaCard",
        { __esModule: true, default: "IfoodPdvOnlineVendaCard" },
      ],
      ["../../api", { __esModule: true, default: { get: async () => ({ data: [] }) } }],
    ]),
  });
  return elements(h.tree).map((node) => node.type);
}

test("PDV online e modo desconhecido exibem resumo externo sem rodape de cobranca", () => {
  for (const summary of [
    { enabled: true, payment_mode: "online" },
    { enabled: false, payment_mode: "unknown" },
  ]) {
    const types = render({ canal: "ifood", ifood_pdv_pilot: summary });
    assert.ok(types.includes("IfoodPdvOnlineVendaCard"));
    assert.equal(types.includes("PDVAcoesFooterCard"), false);
    assert.equal(types.includes("PDVResumoFinanceiroCard"), false);
  }
});

test("app ecommerce e iFood offline conservam resumo e recebimento normais", () => {
  for (const venda of [
    { canal: "app" },
    { canal: "ecommerce" },
    { canal: "ifood", ifood_pdv_pilot: { enabled: true, payment_mode: "offline" } },
  ]) {
    const types = render(venda);
    assert.ok(types.includes("PDVAcoesFooterCard"));
    assert.ok(types.includes("PDVResumoFinanceiroCard"));
    assert.equal(types.includes("IfoodPdvOnlineVendaCard"), false);
  }
});
