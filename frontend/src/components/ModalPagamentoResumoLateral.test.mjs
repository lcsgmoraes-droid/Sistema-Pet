import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../scripts/helpers/reactControllerHarness.mjs";

test("pagamentos e estornos de lote orientam para o histórico sem exclusão individual", () => {
  const excluidos = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./ModalPagamentoResumoLateral.jsx", import.meta.url)),
    {
      mocks: new Map([
        ["lucide-react", { Trash2: "Trash2", Wallet: "Wallet", X: "X" }],
        ["./v2/BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
      ]),
      props: {
        venda: { total: 100, itens: [] },
        valorTotal: 100,
        valorPago: 20,
        valorRestante: 80,
        moduloCampanhasAtivo: false,
        pagamentosExistentes: [
          { id: 1, baixa_lote_id: 7, valor: 80, forma_pagamento: "pix" },
          { id: 2, baixa_lote_id: 7, valor: -80, forma_pagamento: "pix" },
          { id: 3, valor: 20, forma_pagamento: "dinheiro" },
        ],
        pagamentos: [],
        excluirPagamentoExistente: (id) => excluidos.push(id),
      },
    },
  );
  const botoesExcluir = elements(harness.tree).filter(
    (node) => node.type === "BotaoInteracao" && node.props.title === "Excluir pagamento",
  );
  assert.equal(botoesExcluir.length, 1);
  botoesExcluir[0].props.onClick();
  assert.deepEqual(excluidos, [3]);
  assert.match(elementText(harness.tree), /Baixa em lote #7 — consulte o histórico do cliente/);
  assert.match(elementText(harness.tree), /Estorno da baixa em lote #7/);
});
