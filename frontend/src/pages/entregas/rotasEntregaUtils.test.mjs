import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularTempoEstimado,
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
