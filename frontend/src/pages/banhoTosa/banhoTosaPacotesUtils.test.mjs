import assert from "node:assert/strict";
import test from "node:test";
import { formatarCreditos, resumirCreditosAgendamento } from "./banhoTosaPacotesUtils.js";

const contexto = { petId: 10, servicoId: 3, data: "2026-10-27" };
const credito = (extras = {}) => ({
  status: "ativo",
  pet_id: 10,
  data_inicio: "2026-10-01",
  data_validade: "2026-10-31",
  status_pagamento: "pendente",
  servicos: [
    { servico_id: 3, saldo_creditos: "3" },
    { servico_id: 4, saldo_creditos: "2" },
  ],
  ...extras,
});
test("prévia usa o saldo disponível do serviço e permite pagamento pendente", () => {
  assert.deepEqual(resumirCreditosAgendamento([credito()], contexto), {
    saldo: 3,
    pagamentoPendente: true,
  });
  assert.deepEqual(resumirCreditosAgendamento([credito({ status_pagamento: "pago" })], contexto), {
    saldo: 3,
    pagamentoPendente: false,
  });
});
test("prévia não oferece saldo de outro pet, serviço, período ou pacote encerrado", () => {
  for (const item of [
    credito({ pet_id: 11 }),
    credito({ data_inicio: "2026-11-01" }),
    credito({ data_validade: "2026-10-26" }),
    credito({ status: "encerrado" }),
    credito({ servicos: [{ servico_id: 8, saldo_creditos: 4 }] }),
  ]) {
    assert.equal(resumirCreditosAgendamento([item], contexto).saldo, 0);
  }
});
test("validade usa a data do agendamento e inclui limites", () => {
  const legado = credito({
    pet_id: null,
    data_validade: "2026-10-27",
    servicos: [],
    servico_id: null,
    saldo_creditos: 2,
  });
  assert.equal(resumirCreditosAgendamento([legado], contexto).saldo, 0);
  assert.equal(resumirCreditosAgendamento([legado], { ...contexto, data: "2026-10-28" }).saldo, 0);
  assert.equal(
    resumirCreditosAgendamento([credito()], { ...contexto, data: "2026-10-01" }).saldo,
    3,
  );
});

test("saldo fracionado não aparece arredondado como uma unidade inteira", () => {
  assert.equal(formatarCreditos("0.500"), "0,5");
  assert.equal(formatarCreditos("4.000"), "4");
});
