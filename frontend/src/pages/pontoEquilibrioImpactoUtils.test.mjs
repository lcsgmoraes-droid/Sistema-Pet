import assert from "node:assert/strict";
import { test } from "node:test";
import {
  calcularImpactoPontoEquilibrio,
  FAIXAS_PORTE_PETSHOP,
  montarAnaliseCustosPontoEquilibrio,
} from "./pontoEquilibrioImpactoUtils.js";

test("calcula aumento de ponto de equilibrio para novo custo fixo", () => {
  const resultado = calcularImpactoPontoEquilibrio({
    despesasFixas: 10000,
    pontoEquilibrio: 20000,
    margemContribuicaoPercentual: 50,
    faturamento: 18000,
    ticketMedio: 200,
    impactoCustoFixo: 3000,
  });

  assert.equal(resultado.calculavel, true);
  assert.equal(resultado.novoCustoFixo, 13000);
  assert.equal(resultado.impactoPontoEquilibrio, 6000);
  assert.equal(resultado.novoPontoEquilibrio, 26000);
  assert.equal(resultado.novaFaltaFaturar, 8000);
  assert.equal(resultado.vendasImpacto, 30);
});

test("calcula reducao de ponto de equilibrio quando custo fixo diminui", () => {
  const resultado = calcularImpactoPontoEquilibrio({
    despesasFixas: 10000,
    pontoEquilibrio: 20000,
    margemContribuicaoPercentual: 50,
    faturamento: 18000,
    ticketMedio: 200,
    impactoCustoFixo: -1000,
  });

  assert.equal(resultado.calculavel, true);
  assert.equal(resultado.novoCustoFixo, 9000);
  assert.equal(resultado.impactoPontoEquilibrio, -2000);
  assert.equal(resultado.novoPontoEquilibrio, 18000);
  assert.equal(resultado.novaFaltaFaturar, 0);
  assert.equal(resultado.vendasImpacto, -10);
});

test("marca simulacao como indefinida quando margem nao permite calcular", () => {
  const resultado = calcularImpactoPontoEquilibrio({
    despesasFixas: 10000,
    pontoEquilibrio: null,
    margemContribuicaoPercentual: 0,
    faturamento: 18000,
    ticketMedio: 200,
    impactoCustoFixo: 3000,
  });

  assert.equal(resultado.calculavel, false);
  assert.equal(resultado.novoCustoFixo, 13000);
  assert.equal(resultado.impactoPontoEquilibrio, null);
  assert.equal(resultado.novoPontoEquilibrio, null);
});

test("projeta resultado do mes com faturamento informado e aumento de custo fixo", () => {
  const resultado = calcularImpactoPontoEquilibrio({
    despesasFixas: 10000,
    pontoEquilibrio: 20000,
    margemContribuicaoPercentual: 50,
    faturamento: 18000,
    faturamentoProjetado: 30000,
    ticketMedio: 200,
    impactoCustoFixo: 3000,
  });

  assert.equal(resultado.calculavel, true);
  assert.equal(resultado.faturamentoProjetado, 30000);
  assert.equal(resultado.margemContribuicaoProjetada, 15000);
  assert.equal(resultado.resultadoProjetado, 2000);
  assert.equal(resultado.saldoAposSimulacao, 4000);
  assert.equal(resultado.novaFaltaFaturar, 0);
});

test("projeta prejuizo do mes quando faturamento simulado fica abaixo do novo ponto", () => {
  const resultado = calcularImpactoPontoEquilibrio({
    despesasFixas: 10000,
    pontoEquilibrio: 20000,
    margemContribuicaoPercentual: 50,
    faturamento: 18000,
    faturamentoProjetado: 22000,
    ticketMedio: 200,
    impactoCustoFixo: 3000,
  });

  assert.equal(resultado.calculavel, true);
  assert.equal(resultado.margemContribuicaoProjetada, 11000);
  assert.equal(resultado.resultadoProjetado, -2000);
  assert.equal(resultado.saldoAposSimulacao, -4000);
  assert.equal(resultado.novaFaltaFaturar, 4000);
});

test("monta analise de custos com grupos e pareceres percentuais", () => {
  const analise = montarAnaliseCustosPontoEquilibrio({
    porte: "medio",
    dados: {
      faturamento: 50000,
      despesas_fixas: 21000,
      detalhes_classificacao: {
        fixas: [
          { id: 1, descricao: "Aluguel", valor: 10000, origem_classificacao: "Categoria financeira: Aluguel" },
          { id: 2, descricao: "Pro Labore Karine", valor: 3000, origem_classificacao: "Tipo de despesa: Salarios" },
          { id: 3, descricao: "Salarios loja", valor: 7000, origem_classificacao: "Tipo de despesa: Salarios" },
          { id: 4, descricao: "Internet e Telefone", valor: 500, origem_classificacao: "Categoria financeira: Internet" },
          { id: 5, descricao: "Sistema", valor: 500, origem_classificacao: "Categoria financeira: Sistema" },
        ],
      },
    },
  });

  const aluguel = analise.pareceres.find((item) => item.id === "aluguel");
  const folha = analise.pareceres.find((item) => item.id === "folha");

  assert.equal(analise.grupos.find((item) => item.id === "aluguel").valor, 10000);
  assert.equal(analise.grupos.find((item) => item.id === "folha").valor, 10000);
  assert.equal(aluguel.percentualFaturamento, 20);
  assert.equal(aluguel.referenciaPercentual, 13);
  assert.equal(aluguel.diferencaPercentual, 7);
  assert.equal(aluguel.diferencaValor, 3500);
  assert.equal(aluguel.status, "acima");
  assert.equal(folha.percentualFaturamento, 20);
  assert.equal(folha.status, "saudavel");
});

test("define faixas gerenciais mensais para porte do petshop", () => {
  assert.deepEqual(
    FAIXAS_PORTE_PETSHOP.map((porte) => [porte.id, porte.label, porte.faixaMensal]),
    [
      ["pequeno", "Pequeno", "Ate R$ 80 mil/mes"],
      ["medio", "Medio", "R$ 80 mil a R$ 250 mil/mes"],
      ["grande", "Grande", "Acima de R$ 250 mil/mes"],
    ],
  );
});

test("ajusta referencia de aluguel conforme porte selecionado", () => {
  const dados = {
    faturamento: 50000,
    despesas_fixas: 10000,
    detalhes_classificacao: {
      fixas: [
        { id: 1, descricao: "Aluguel", valor: 6500, origem_classificacao: "Categoria financeira: Aluguel" },
      ],
    },
  };

  const pequeno = montarAnaliseCustosPontoEquilibrio({ dados, porte: "pequeno" });
  const grande = montarAnaliseCustosPontoEquilibrio({ dados, porte: "grande" });

  assert.equal(pequeno.porte.id, "pequeno");
  assert.equal(pequeno.pareceres.find((item) => item.id === "aluguel").referenciaPercentual, 14);
  assert.equal(grande.porte.id, "grande");
  assert.equal(grande.pareceres.find((item) => item.id === "aluguel").referenciaPercentual, 10);
});
