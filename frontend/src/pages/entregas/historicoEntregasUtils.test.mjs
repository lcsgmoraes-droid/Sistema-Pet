import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularPeriodoRapidoHistorico,
  calcularResumoHistorico,
  formatarDuracao,
  montarParametrosHistorico,
  obterDistanciaRota,
  obterQuantidadeEntregas,
} from "./historicoEntregasUtils.js";

test("calcula atalhos de periodo usando datas locais e intervalos inclusivos", () => {
  const base = new Date(2026, 6, 17, 18, 30);

  assert.deepEqual(calcularPeriodoRapidoHistorico("hoje", base), {
    dataInicio: "2026-07-17",
    dataFim: "2026-07-17",
  });
  assert.deepEqual(calcularPeriodoRapidoHistorico("ontem", base), {
    dataInicio: "2026-07-16",
    dataFim: "2026-07-16",
  });
  assert.deepEqual(calcularPeriodoRapidoHistorico("ultimos_7_dias", base), {
    dataInicio: "2026-07-11",
    dataFim: "2026-07-17",
  });
  assert.deepEqual(calcularPeriodoRapidoHistorico("este_mes", base), {
    dataInicio: "2026-07-01",
    dataFim: "2026-07-17",
  });
});

test("resume rotas usando entregas reais e custo medio por entrega", () => {
  const resumo = calcularResumoHistorico([
    {
      total_entregas: 3,
      distancia_real: 12.5,
      custo_real: 30,
      taxa_total_entregas: 45,
      valor_total_vendas: 300,
    },
    {
      paradas: [{}, {}],
      km_inicial: 100,
      km_final: 108,
      custo_real: 20,
      taxa_entrega_cliente: 25,
      valor_total_vendas: 200,
    },
  ]);

  assert.deepEqual(resumo, {
    rotas: 2,
    entregas: 5,
    distancia: 20.5,
    custo: 50,
    taxas: 70,
    vendas: 500,
    custoMedio: 10,
    resultadoEntrega: 20,
  });
});

test("usa fallbacks seguros para quantidade, distancia e duracao", () => {
  assert.equal(obterQuantidadeEntregas({ venda_id: 1 }), 1);
  assert.equal(obterDistanciaRota({ distancia_total_km_real: 7.25 }), 7.25);
  assert.equal(formatarDuracao(135), "2h 15min");
  assert.equal(formatarDuracao(null), "Não informado");
});

test("monta somente filtros preenchidos", () => {
  assert.deepEqual(
    montarParametrosHistorico({
      dataInicio: "2026-07-01",
      dataFim: "2026-07-17",
      entregadorId: 9,
      busca: "  Maria  ",
      ordenarPor: "entregas",
      direcao: "asc",
    }),
    {
      status: "concluida",
      data_inicio: "2026-07-01",
      data_fim: "2026-07-17",
      entregador_id: 9,
      busca: "Maria",
      ordenar_por: "entregas",
      direcao: "asc",
      limite: 500,
    },
  );
});
