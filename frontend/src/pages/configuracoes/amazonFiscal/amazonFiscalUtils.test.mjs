import assert from "node:assert/strict";
import test from "node:test";
import { accountPayload, canIssueOrder, fiscalError } from "./amazonFiscalUtils.js";

test("guardas não confundem autorização SEFAZ, estado desconhecido ou snapshot incompleto com pedido emitível", () => {
  const order = { status: "ready", blockers: [], source_revision: 1, payload_hash: "hash" };
  assert.equal(canIssueOrder(order), true);
  for (const patch of [
    { status: "authorized" },
    { status: "unknown" },
    { blockers: [{ message: "CPF ausente" }] },
    { source_revision: 0 },
    { payload_hash: "" },
    { blockers: undefined },
  ])
    assert.equal(canIssueOrder({ ...order, ...patch }), false);
});

test("configuração não envia datas ou permissões inventadas e rejeita política inválida", () => {
  const account = accountPayload({
    seller_id: " QA ",
    emitter_cnpj: "11222333000181",
    activated_at: "2000-01-01",
    scopes: ["fiscal:issue"],
  });
  assert.equal(account.seller_id, "QA");
  assert.equal(account.discount_policy, "source_discounts");
  assert.equal(account.auto_issue_enabled, false);
  assert.equal(account.upload_enabled, false);
  assert.equal(account.active, false);
  assert.equal(accountPayload({ ...account, upload_enabled: true }).upload_enabled, true);
  assert.equal("scopes" in account, false);
  assert.equal("activated_at" in account, false);
  assert.throws(() => accountPayload({ ...account, discount_policy: "inventada" }), /política/);
});

test("erro Blob exibe mensagem fiscal útil; HTML de proxy não vaza para operador", async () => {
  const error = {
    response: { data: new Blob([JSON.stringify({ detail: "Conexão sem fiscal:issue." })]) },
  };
  assert.equal(await fiscalError(error), "Conexão sem fiscal:issue.");
  assert.doesNotMatch(
    await fiscalError({ response: { data: "<html>502 Bad Gateway</html>" } }),
    /<html>|Bad Gateway/,
  );
});
