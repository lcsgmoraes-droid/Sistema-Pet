import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularTempoEstimado,
  agruparRotasPorEntregador,
  filtrarRotasEmAndamento,
  formatarTempo,
  formatarHorarioLocalizacao,
  getStatusColor,
  getStatusLabel,
  getUltimaParadaPendente,
  montarDestinoMapaRota,
} from "./rotasEntregaUtils.js";

test("calcula e formata tempo estimado da ultima parada", () => {
  assert.equal(
    calcularTempoEstimado({
      paradas: [{ tempo_acumulado: 300 }, { tempo_acumulado: 3900 }],
    }),
    3900,
  );

  assert.equal(formatarTempo(3900), "1h5min");
  assert.equal(formatarTempo(900), "15min");
  assert.equal(formatarTempo(null), "N/A");
});

test("retorna cores e labels dos status conhecidos", () => {
  assert.equal(getStatusColor("pendente"), "#FFA500");
  assert.equal(getStatusColor("em_rota"), "#007BFF");
  assert.equal(getStatusColor("concluida"), "#28A745");
  assert.equal(getStatusColor("desconhecido"), "#6C757D");

  assert.equal(getStatusLabel("pendente"), "🟠 Pendente");
  assert.equal(getStatusLabel("em_andamento"), "🔵 Em Andamento");
  assert.equal(getStatusLabel("cancelada"), "❌ Cancelada");
  assert.equal(getStatusLabel("custom"), "custom");
});

test("filtra rotas em andamento e agrupa por entregador", () => {
  const rotas = [
    { id: 1, status: "pendente", entregador: { id: 10, nome: "Ana" } },
    { id: 2, status: "em_rota", entregador: { id: 10, nome: "Ana" } },
    { id: 3, status: "em_andamento", entregador: { id: 11, nome: "Bruno" } },
    { id: 4, status: "concluida", entregador: { id: 11, nome: "Bruno" } },
    { id: 5, status: "em_rota", entregador: null },
  ];

  const emAndamento = filtrarRotasEmAndamento(rotas);
  assert.deepEqual(
    emAndamento.map((rota) => rota.id),
    [2, 3, 5],
  );

  assert.deepEqual(agruparRotasPorEntregador(emAndamento), {
    10: {
      entregadorNome: "Ana",
      rotas: [rotas[1]],
    },
    11: {
      entregadorNome: "Bruno",
      rotas: [rotas[2]],
    },
    "sem-id-5": {
      entregadorNome: "Entregador não informado",
      rotas: [rotas[4]],
    },
  });
});

test("formata horario de localizacao e protege datas invalidas", () => {
  assert.equal(formatarHorarioLocalizacao(null), "Sem atualização");
  assert.equal(formatarHorarioLocalizacao("data-invalida"), "Sem atualização");
  assert.match(formatarHorarioLocalizacao("2026-05-27T12:34:56Z"), /^\d{2}:\d{2}:\d{2}$/);
});

test("encontra a proxima parada pendente com fallback para a ultima", () => {
  const rota = {
    paradas: [
      { id: 1, status: "entregue" },
      { id: 2, status: "pendente" },
      { id: 3, status: "pendente" },
    ],
  };

  assert.deepEqual(getUltimaParadaPendente(rota), { id: 2, status: "pendente" });
  assert.deepEqual(getUltimaParadaPendente({ paradas: [{ id: 4, status: "entregue" }] }), {
    id: 4,
    status: "entregue",
  });
  assert.equal(getUltimaParadaPendente({}), null);
});

test("monta destino de mapa por prioridade sem abrir janela", () => {
  assert.deepEqual(
    montarDestinoMapaRota({ token_rastreio: "abc 123" }),
    {
      url: "/rastreio/abc%20123",
      tipo: "rastreio",
    },
  );

  assert.deepEqual(
    montarDestinoMapaRota({ lat_atual: -23.5, lon_atual: -46.6 }),
    {
      url: "https://www.google.com/maps?q=-23.5,-46.6",
      tipo: "coordenadas",
    },
  );

  assert.deepEqual(
    montarDestinoMapaRota({
      paradas: [{ status: "entregue", endereco: "Rua A" }, { status: "pendente", endereco: "Rua B" }],
    }),
    {
      url: "https://www.google.com/maps/search/?api=1&query=Rua%20B",
      tipo: "endereco",
    },
  );

  assert.equal(montarDestinoMapaRota({}), null);
});
