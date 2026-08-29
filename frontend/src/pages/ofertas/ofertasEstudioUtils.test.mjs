import assert from "node:assert/strict";

import {
  agruparPaginas,
  calcularDesconto,
  calcularMargem,
  criarItemSelecionado,
  criarPeriodo,
  montarPayloadPublicacao,
} from "./ofertasEstudioUtils.js";

assert.equal(calcularDesconto(100, 75), 25);
assert.equal(calcularDesconto(100, 120), 0);
assert.equal(calcularMargem(50, 30), 40);
assert.equal(agruparPaginas(Array.from({ length: 13 }), "jornal", "quadrado").length, 3);
assert.equal(agruparPaginas(Array.from({ length: 3 }), "individual", "story").length, 3);

const selecionado = criarItemSelecionado(
  {
    id: 8,
    preco_erp: 40,
    preco_sugerido_validade: 30,
    lote_validade: { id: 9 },
    imagem_url: "/produto.webp",
  },
  true,
);
assert.equal(selecionado.preco_arte, 30);
assert.equal(selecionado.lote_id, 9);
assert.equal(selecionado.mostrar_validade, true);

const periodo = criarPeriodo("semanal", new Date("2026-08-29T12:00:00-03:00"));
assert.ok(periodo.inicio);
assert.ok(periodo.fim);
const periodoDiarioNoFimDoDia = criarPeriodo("diaria", new Date("2026-08-29T23:59:30-03:00"));
assert.ok(new Date(periodoDiarioNoFimDoDia.fim) > new Date(periodoDiarioNoFimDoDia.inicio));

const payload = montarPayloadPublicacao({
  titulo: " Jornal da semana ",
  periodicidade: "semanal",
  tipoArte: "jornal",
  formato: "quadrado",
  inicio: "2026-08-29T12:00",
  fim: "2026-09-05T12:00",
  expira: "2026-09-05T12:00",
  itens: [selecionado],
  tema: "premium",
});
assert.equal(payload.titulo, "Jornal da semana");
assert.equal(payload.produtos[0].imagem_url, "/produto.webp");
assert.equal(payload.produtos[0].lote_id, 9);

console.log("ofertasEstudioUtils: ok");
