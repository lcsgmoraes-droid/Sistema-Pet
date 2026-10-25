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

test("margem com cobranças completas não depende de recebimento bancário e simulação não libera lucro real", () => {
  const bridge = {
    payment_mode: "online",
    payment: { status: "approved" },
    receivable: { received_amount: 0 },
    ifood_financial: { complete: true, charges: [], pending_components: [] },
    ifood_rentabilidade: {
      lucro: 17.46,
      margem_sobre_venda: 26.9,
      rentabilidade_status: "complete",
    },
  };
  const text = elementText(render(bridge));
  assert.match(text, /Contribuição da venda:.*17,46.*26,9%/s);
  assert.match(text, /Repasse a conciliar/);
  assert.match(text, /não confirma recebimento no banco/);
  assert.doesNotMatch(text, /margem aguardam o Financial/);
  const simulada = elementText(
    render({
      ...bridge,
      ifood_financial: { complete: false, simulated: true, simulation_complete: true },
      ifood_rentabilidade: {
        lucro: null,
        margem_sobre_venda: null,
        rentabilidade_status: "pending_ifood_financial",
      },
    }),
  );
  assert.doesNotMatch(simulada, /Contribuição da venda:/);
});

test("cancelamento local preserva pagamento original sem afirmar reembolso ou margem", () => {
  for (const paymentStatus of ["approved", "platform_responsibility"]) {
    const text = elementText(
      render({
        status: "cancelled",
        payment_mode: "online",
        payment: { status: paymentStatus },
        receivable: { status: "cancelled_pending_provider_review", received_amount: 0 },
        ifood_rentabilidade: { lucro: 17.46, rentabilidade_status: "complete" },
      }),
    );
    assert.match(text, /Cancelamento registrado no CorePet/);
    assert.match(text, /pagamento original do pedido permanece no histórico/);
    assert.match(text, /Estorno iFood a conferir/);
    assert.match(text, /não cancela o pedido no iFood nem comprova devolução ao consumidor/);
    assert.match(text, /nenhum reembolso foi lançado em caixa ou banco/);
    assert.doesNotMatch(text, /Contribuição da venda|Repasse a conciliar|margem aguardam/);
  }
});
