import assert from "node:assert/strict";
import test from "node:test";
import {
  currentSequence,
  formatSequence,
  numberingRows,
  prepareNumbering,
} from "./intnfeNumeracao.mjs";

const rows = [
  { serie: "003", ambienteCodigo: 2, modelo: 55, ultimoNumero: 1, proximoNumero: 2 },
  { serie: "3", ambienteCodigo: 1, modelo: 55, ultimoNumero: 4500, proximoNumero: 4501 },
  { serie: "3", ambienteCodigo: 2, modelo: 65, ultimoNumero: 99, proximoNumero: 100 },
];
const form = { serie: "003", ambiente_codigo: "2", proximo_numero: "4501" };

test("revisão identifica ambiente, modelo, série e número consultado", () => {
  assert.deepEqual(prepareNumbering(rows, form).payload, {
    serie: "003",
    ambiente_codigo: 2,
    modelo: 55,
    proximo_numero: 4501,
    ultimo_numero_consultado: 1,
  });
  assert.equal(currentSequence(rows, "3", "1").ultimoNumero, 4500);
  assert.equal(formatSequence(4501), "4.501");
});
test("bloqueia repetição, retrocesso, decimais e formatos ambíguos", () => {
  for (const proximo_numero of ["", "0", "1", "2", "4.501", "45,01", "4e3", "-5", "1000000000"]) {
    assert.ok(prepareNumbering(rows, { ...form, proximo_numero }).error, proximo_numero);
  }
  assert.ok(prepareNumbering(rows, { ...form, ambiente_codigo: "1" }).error);
});
test("série nova começa no 1 e só precisa ajustar para continuar acima dele", () => {
  assert.ok(prepareNumbering([], { ...form, serie: "0", proximo_numero: "1" }).error);
  assert.equal(prepareNumbering([], { ...form, serie: "0" }).payload.ultimo_numero_consultado, 0);
  assert.ok(prepareNumbering(rows, { ...form, serie: "890" }).error);
  assert.ok(prepareNumbering(rows, { ...form, ambiente_codigo: "3" }).error);
  assert.ok(prepareNumbering(null, form).error);
});
test("resposta inválida não vira numeração vazia; série esgotada não avança", () => {
  assert.deepEqual(numberingRows({ series: rows }), rows);
  for (const series of [
    null,
    [...rows, rows[0]],
    [{ ...rows[0], proximoNumero: 1 }],
    [{ ...rows[0], modelo: 99 }],
  ]) {
    assert.throws(() => numberingRows({ series }));
  }
  const exhausted = [{ ...rows[0], ultimoNumero: 999999999, proximoNumero: 1000000000 }];
  assert.ok(prepareNumbering(exhausted, form).error.includes("limite"));
});
