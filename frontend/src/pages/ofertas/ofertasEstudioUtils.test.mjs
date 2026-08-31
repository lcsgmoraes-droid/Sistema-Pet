import assert from "node:assert/strict";

import {
  agruparPaginas,
  calcularDesconto,
  calcularDimensoesCaptura,
  calcularMargem,
  criarItemSelecionado,
  criarPeriodo,
  itensPorPagina,
  layoutJornal,
  montarPayloadPublicacao,
  obterTituloProdutoArte,
  resumirTextoArte,
} from "./ofertasEstudioUtils.js";

assert.equal(calcularDesconto(100, 75), 25);
assert.equal(calcularDesconto(100, 120), 0);
assert.equal(calcularMargem(50, 30), 40);
assert.equal(itensPorPagina("jornal", "quadrado"), 4);
assert.equal(itensPorPagina("jornal", "retrato"), 6);
assert.deepEqual(layoutJornal("story"), { colunas: 2, linhas: 3, itens: 6 });
assert.equal(agruparPaginas(Array.from({ length: 13 }), "jornal", "quadrado").length, 4);
assert.equal(agruparPaginas(Array.from({ length: 3 }), "individual", "story").length, 3);

for (const formato of ["quadrado", "retrato", "story", "a4"]) {
  const dimensoes = calcularDimensoesCaptura(formato);
  assert.equal(Math.round(dimensoes.largura * dimensoes.escala), dimensoes.larguraFinal);
  assert.equal(Math.round(dimensoes.altura * dimensoes.escala), dimensoes.alturaFinal);
}
assert.equal(resumirTextoArte(" Produto   com   espaços ", 40), "Produto com espaços");
assert.equal(resumirTextoArte("abcdefghij", 6), "abcde…");
assert.equal(resumirTextoArte("Ração super premium para cães adultos", 25), "Ração super premium…");

const tituloJornalLongo = obterTituloProdutoArte(
  "SUPLEMENTO ALIMENTAR SUPER PREMIUM PARA CÃES ADULTOS DE RAÇAS GRANDES 15KG",
  "jornal",
  "quadrado",
);
assert.equal(tituloJornalLongo.linhas, 2);
assert.equal(tituloJornalLongo.tamanho, "longo");
assert.ok(tituloJornalLongo.texto.endsWith("…"));

const tituloIndividualLongo = obterTituloProdutoArte(
  "Antipulgas, carrapatos e vermes para cães adultos de 10,1 a 25kg com três tabletes mastigáveis em embalagem econômica",
  "individual",
  "story",
);
assert.equal(tituloIndividualLongo.linhas, 3);
assert.equal(tituloIndividualLongo.tamanho, "longo");
assert.equal(tituloIndividualLongo.texto.endsWith("…"), false);

const tituloIndividualExtenso = obterTituloProdutoArte(
  "Ração Super Premium para Cães Adultos de Raças Grandes com Frango, Arroz, Ômega 3 e Controle de Peso - Embalagem Econômica 15kg com Fórmula Especial",
  "individual",
  "quadrado",
);
assert.equal(tituloIndividualExtenso.tamanho, "longo");
assert.ok(tituloIndividualExtenso.texto.endsWith("…"));
assert.equal(tituloIndividualExtenso.texto.endsWith(" Fórm…"), false);
assert.equal(tituloIndividualExtenso.texto.includes("-…"), false);

const selecionado = criarItemSelecionado(
  {
    id: 8,
    preco_erp: 40,
    preco_sugerido_validade: 30,
    lote_validade: { id: 9 },
    imagem_url: "/produto.webp",
    imagens: [
      { id: 1, url: "/produto.webp" },
      { id: 2, url: "/produto-verso.webp" },
    ],
  },
  true,
);
assert.equal(selecionado.preco_arte, 30);
assert.equal(selecionado.lote_id, 9);
assert.equal(selecionado.mostrar_validade, true);
assert.equal(selecionado.imagens_disponiveis.length, 2);

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
  exibirApp: true,
  exibirEcommerce: false,
});
assert.equal(payload.titulo, "Jornal da semana");
assert.equal(payload.produtos[0].imagem_url, "/produto.webp");
assert.equal(payload.produtos[0].lote_id, 9);
assert.deepEqual(payload.configuracao.canais, { app: true, ecommerce: false });

console.log("ofertasEstudioUtils: ok");
