import assert from "node:assert/strict";
import { test } from "node:test";

import { montarTextoSaldoCredito } from "../utils/saldoCreditoPrint.js";

test("montarTextoSaldoCredito identifica cliente, saldo e momento da consulta", () => {
  const texto = montarTextoSaldoCredito(
    { id: 12, codigo: "CLI-12", nome: "João da Silva" },
    17555.25,
    new Date("2026-09-04T12:30:00Z"),
  );

  assert.match(texto, /COMPROVANTE DE CREDITO/);
  assert.match(texto, /Cliente: Joao da Silva/);
  assert.match(texto, /Codigo: CLI-12/);
  assert.match(texto, /R\$ 17\.555,25/);
});
