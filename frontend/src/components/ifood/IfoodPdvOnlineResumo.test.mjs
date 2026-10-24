import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

function render(bridge) {
  return createControllerHarness(
    fileURLToPath(new URL("./IfoodPdvOnlineResumo.jsx", import.meta.url)),
    { mocks: new Map(), props: { bridge } },
  ).tree;
}

test("online discrimina valor do consumidor, servico iFood e repasse desconhecido", () => {
  const text = elementText(
    render({
      payment_mode: "online",
      checkout: {
        items_total: 65,
        delivery_fee: 8.9,
        ifood_service_fee: 1.99,
        operational_total: 73.9,
        customer_total: 75.89,
      },
      payment: { status: "platform_responsibility" },
      receivable: {
        status: "awaiting_financial",
        received_amount: 0,
        net_amount: null,
        expected_date: null,
        margin_status: "pending",
      },
    }),
  );
  for (const value of ["65,00", "8,90", "1,99", "73,90", "75,89"]) assert.ok(text.includes(value));
  assert.match(text, /sob responsabilidade do iFood/);
  assert.match(text, /taxa de serviço pertence ao iFood/);
  assert.match(text, /Repasse a conciliar/);
  assert.match(text, /Nenhum recebimento em caixa ou banco registrado/);
  assert.match(text, /margem aguardam o Financial/);
  assert.doesNotMatch(text, /Pagamento externo registrado|R\$\s*0,00/);
});

test("dados monetarios desconhecidos nao viram zero e offline nao exibe comprovacao online", () => {
  assert.equal(render({ payment_mode: "offline" }), null);
  const text = elementText(render({ payment_mode: "online", payment: { status: "approved" } }));
  assert.match(text, /Pagamento externo registrado/);
  assert.equal((text.match(/Não informado/g) || []).length, 5);
  assert.doesNotMatch(text, /R\$\s*0,00/);
});
