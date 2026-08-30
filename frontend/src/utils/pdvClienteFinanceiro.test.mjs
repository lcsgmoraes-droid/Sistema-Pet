import assert from "node:assert/strict";

import { calcularResumoEmAbertoCliente } from "./pdvClienteFinanceiro.js";

assert.deepEqual(
  calcularResumoEmAbertoCliente({
    total_vendas: 3,
    total_em_aberto: 188.36,
    total_parcelas_crediario: 9,
    total_crediario_em_aberto: 328.72,
    total_crediario_vencido: 27.22,
  }),
  {
    total_vendas: 3,
    total_parcelas_crediario: 9,
    total_vendas_em_aberto: 188.36,
    total_crediario_em_aberto: 328.72,
    total_crediario_vencido: 27.22,
    total_geral_em_aberto: 517.08,
  },
);

assert.deepEqual(calcularResumoEmAbertoCliente(), {
  total_vendas: 0,
  total_parcelas_crediario: 0,
  total_vendas_em_aberto: 0,
  total_crediario_em_aberto: 0,
  total_crediario_vencido: 0,
  total_geral_em_aberto: 0,
});

assert.deepEqual(
  calcularResumoEmAbertoCliente({
    total_vendas: "2.9",
    total_em_aberto: "10.10",
    total_parcelas_crediario: "4",
    total_crediario_em_aberto: "20.20",
    total_crediario_vencido: Number.NaN,
  }),
  {
    total_vendas: 2,
    total_parcelas_crediario: 4,
    total_vendas_em_aberto: 10.1,
    total_crediario_em_aberto: 20.2,
    total_crediario_vencido: 0,
    total_geral_em_aberto: 30.3,
  },
);

console.log("pdvClienteFinanceiro: ok");
