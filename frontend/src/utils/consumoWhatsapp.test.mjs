import assert from "node:assert/strict";
import { test } from "node:test";
import { avisosDeCusto, leituraDaDivergencia, rotulo, ultimosMeses } from "./consumoWhatsapp.js";

test("ultimosMeses lista do mês atual para trás, atravessando o ano", () => {
  const meses = ultimosMeses(3, new Date(2026, 0, 15));

  assert.deepEqual(
    meses.map((mes) => mes.value),
    ["2026-01", "2025-12", "2025-11"],
  );
  assert.match(meses[0].label, /^Janeiro de 2026$/);
});

test("avisosDeCusto avisa de tarifa faltando e de cobrança ainda não informada", () => {
  assert.equal(avisosDeCusto({ cobraveis_sem_tarifa: 0, sem_informacao_de_cobranca: 0 }).length, 0);
  const avisos = avisosDeCusto({ cobraveis_sem_tarifa: 2, sem_informacao_de_cobranca: 5 });
  assert.equal(avisos.length, 2);
  assert.match(avisos[0], /sem tarifa/);
});

test("leituraDaDivergencia explica em texto, nunca só em cor", () => {
  assert.match(leituraDaDivergencia(null).texto, /ainda não informada/);
  assert.equal(leituraDaDivergencia(0).texto, "Confere com a fatura");
  assert.match(leituraDaDivergencia(1.5).texto, /acima do estimado/);
  assert.match(leituraDaDivergencia(-0.8).texto, /abaixo do estimado/);
});

test("rotulo devolve a própria chave quando não conhece", () => {
  assert.equal(rotulo({ a: "A" }, "a"), "A");
  assert.equal(rotulo({ a: "A" }, "x"), "x");
});

test("avisoDoSaldo só avisa quando o controle está ligado e o saldo está baixo ou esgotado", async () => {
  const { avisoDoSaldo, formatarCreditos } = await import("./consumoWhatsapp.js");

  assert.equal(avisoDoSaldo({ controle_ativo: false, nivel: "esgotado" }), null);
  assert.equal(avisoDoSaldo({ controle_ativo: true, nivel: "ok" }), null);
  assert.equal(avisoDoSaldo({ controle_ativo: true, nivel: "esgotado" }).tom, "erro");
  assert.match(
    avisoDoSaldo({ controle_ativo: true, nivel: "baixo", disponivel: 40 }).texto,
    /40 créditos/,
  );
  assert.equal(formatarCreditos(1500), "1.500 créditos");
});
