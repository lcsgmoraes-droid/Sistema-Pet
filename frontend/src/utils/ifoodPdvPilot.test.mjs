import assert from "node:assert/strict";
import test from "node:test";
import { canFinalizeIfoodOnlinePdvPilot, isIfoodManualPaymentBlocked } from "./ifoodPdvPilot.js";

test("cobranca manual iFood exige modo offline habilitado; outros canais preservam fluxo", () => {
  assert.equal(isIfoodManualPaymentBlocked({ canal: "ifood" }), true);
  for (const summary of [
    { enabled: true, payment_mode: "online" },
    { enabled: false, payment_mode: "offline" },
    { enabled: false, payment_mode: "unknown" },
    { enabled: true, payment_mode: null },
  ]) {
    assert.equal(isIfoodManualPaymentBlocked({ canal: "ifood", ifood_pdv_pilot: summary }), true);
  }
  assert.equal(
    isIfoodManualPaymentBlocked({
      canal: "ifood",
      ifood_pdv_pilot: { enabled: true, payment_mode: "offline" },
    }),
    false,
  );
  for (const canal of ["app", "ecommerce", "loja_fisica", "whatsapp"]) {
    assert.equal(isIfoodManualPaymentBlocked({ canal }), false);
  }
});

test("conclusao online exige capacidade explicita do servidor e reserva existente", () => {
  const bridge = {
    enabled: true,
    eligible: false,
    payment_mode: "online",
    can_finalize_online: true,
    status: "reserved",
    sale_id: 42,
    ifood_order_id: "test-order",
  };
  assert.equal(canFinalizeIfoodOnlinePdvPilot(bridge), true);
  for (const patch of [
    { enabled: false },
    { can_finalize_online: false },
    { status: "sold" },
    { payment_mode: "offline" },
    { sale_id: null },
    { ifood_order_id: null },
  ]) {
    assert.equal(canFinalizeIfoodOnlinePdvPilot({ ...bridge, ...patch }), false);
  }
});
