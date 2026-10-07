import assert from "node:assert/strict";
import {
  compararPeriodosDRE,
  dadosCorrespondemParametrosDRE,
  extrairIndicadoresDRE,
  obterParametrosMesAnterior,
} from "./analiseInteligenteUtils.js";

const atual = {
  receita_bruta: 9999,
  totais: {
    receita_bruta: 1200,
    receita_liquida: 1000,
    cmv: 300,
    custos_diretos: 400,
    lucro_bruto: 600,
    despesas_operacionais: 250,
    lucro_liquido: 350,
    margem_bruta: 60,
    margem_liquida: 35,
  },
  linhas: [
    { campo: "despesas_administrativas", valor: 30, canal: "loja_fisica" },
    { campo: "despesas_administrativas", valor: 20, canal: "mercado_livre" },
    { campo: "cmv", valor: 300, canal: "loja_fisica" },
  ],
};

assert.deepEqual(extrairIndicadoresDRE(atual), {
  receitaBruta: 1200,
  receitaLiquida: 1000,
  cmv: 300,
  custosDiretos: 400,
  lucroBruto: 600,
  despesasOperacionais: 250,
  despesasAdmin: 50,
  lucroLiquido: 350,
  margemBruta: 60,
  margemLiquida: 35,
});

const anterior = {
  totais: {
    receita_bruta: 1000,
    despesas_operacionais: 200,
    lucro_liquido: 250,
    margem_liquida: 30,
  },
};

assert.deepEqual(compararPeriodosDRE(atual, anterior), {
  receita: { atual: 1200, anterior: 1000, variacao: 20 },
  lucro: { atual: 350, anterior: 250, variacao: 40 },
  despesas: { atual: 250, anterior: 200, variacao: 25 },
  margem: { atual: 35, anterior: 30, variacao: 5 },
});
assert.equal(compararPeriodosDRE(atual, { totais: {} }).receita.variacao, null);

assert.deepEqual(
  obterParametrosMesAnterior({ ano: "2026", mes: "01", canais: "loja_fisica,app" }),
  {
    ano: 2025,
    mes: 12,
    canais: "loja_fisica,app",
  },
);
assert.deepEqual(obterParametrosMesAnterior({ ano: 2026, mes: 10, canais: "shopee" }), {
  ano: 2026,
  mes: 9,
  canais: "shopee",
});
assert.equal(
  obterParametrosMesAnterior({ ano: 2026, mes: 10, mes_inicial: 1, canais: "app" }),
  null,
);
assert.equal(obterParametrosMesAnterior({ ano: 2026, mes: 10, data_final: "2026-10-05" }), null);

const resposta = {
  ...atual,
  ano: 2026,
  mes: 10,
  mes_inicial: 10,
  data_final: null,
  canais_encontrados: ["loja_fisica", "app"],
};
const parametros = { ano: "2026", mes: "10", canais: "loja_fisica,app" };
assert.equal(dadosCorrespondemParametrosDRE(resposta, parametros), true);
assert.equal(dadosCorrespondemParametrosDRE(resposta, { ...parametros, mes: "11" }), false);
assert.equal(dadosCorrespondemParametrosDRE(resposta, { ...parametros, canais: "shopee" }), false);
assert.equal(
  dadosCorrespondemParametrosDRE(resposta, { ...parametros, data_final: "2026-10-05" }),
  false,
);

console.log("Análise Inteligente da DRE canônica validada com sucesso.");
