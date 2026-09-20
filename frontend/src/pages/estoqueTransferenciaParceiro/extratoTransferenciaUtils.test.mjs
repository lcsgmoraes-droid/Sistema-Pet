import assert from "node:assert/strict";
import { test } from "node:test";

import {
  criarExtratoTransferenciaVazio,
  filtrarItensExtratoTransferencia,
} from "./extratoTransferenciaUtils.js";

test("factory do extrato inicia saldos e listas vazios", () => {
  const extrato = criarExtratoTransferenciaVazio({ totais: { saldo_final: 25 } });
  assert.deepEqual(extrato.items, []);
  assert.equal(extrato.totais.saldo_anterior, 0);
  assert.equal(extrato.totais.saldo_final, 25);
});

test("filtros do extrato separam dividas, creditos e documentos em aberto", () => {
  const items = [
    { id: "d1", tipo: "divida", credito: 0, saldo_documento: 100, conta_status: "vencido" },
    { id: "d2", tipo: "divida", credito: 0, saldo_documento: 0, conta_status: "recebido" },
    { id: "p1", tipo: "pagamento", credito: 50, saldo_documento: 100, conta_status: "parcial" },
  ];

  assert.deepEqual(
    filtrarItensExtratoTransferencia(items, "dividas").map((item) => item.id),
    ["d1", "d2"],
  );
  assert.deepEqual(
    filtrarItensExtratoTransferencia(items, "creditos").map((item) => item.id),
    ["p1"],
  );
  assert.deepEqual(
    filtrarItensExtratoTransferencia(items, "em_aberto").map((item) => item.id),
    ["d1"],
  );
});
