import assert from "node:assert/strict";
import test from "node:test";

import {
  adicionarPontoTrilha,
  coordenadasDaRota,
  gerarPontosSimulacao,
  obterEstadoSinal,
  simuladorRastreioHabilitado,
} from "./rastreamentoAoVivoUtils.js";

test("valida coordenadas e classifica idade do sinal", () => {
  const agora = Date.parse("2026-08-27T12:00:00Z");
  const rota = { lat_atual: "-22.12", lon_atual: "-51.4" };

  assert.deepEqual(coordenadasDaRota(rota), { latitude: -22.12, longitude: -51.4 });
  assert.equal(coordenadasDaRota({ lat_atual: null, lon_atual: null }), null);
  assert.equal(coordenadasDaRota({ lat_atual: "", lon_atual: "" }), null);
  assert.equal(
    obterEstadoSinal({ ...rota, localizacao_atualizada_em: "2026-08-27T11:59:45Z" }, agora).key,
    "ao_vivo",
  );
  assert.equal(
    obterEstadoSinal({ ...rota, localizacao_atualizada_em: "2026-08-27T11:59:00Z" }, agora).key,
    "atrasado",
  );
  assert.equal(
    obterEstadoSinal({ ...rota, localizacao_atualizada_em: "2026-08-27T11:50:00Z" }, agora).key,
    "offline",
  );
});

test("trilha ignora ponto repetido e respeita limite", () => {
  const primeiro = { latitude: -22, longitude: -51 };
  assert.deepEqual(adicionarPontoTrilha([primeiro], primeiro), [primeiro]);
  assert.deepEqual(adicionarPontoTrilha([primeiro], { latitude: -22.1, longitude: -51.1 }, 1), [
    { latitude: -22.1, longitude: -51.1 },
  ]);
});

test("gera percurso curto a partir da posição atual", () => {
  const pontos = gerarPontosSimulacao({ latitude: -22.12, longitude: -51.4 });
  assert.equal(pontos.length, 12);
  assert.deepEqual(pontos[0], { latitude: -22.12, longitude: -51.4 });
  assert.notDeepEqual(pontos[5], pontos[0]);
});

test("simulador fica bloqueado em produção", () => {
  assert.equal(simuladorRastreioHabilitado({ DEV: true, MODE: "development" }), true);
  assert.equal(
    simuladorRastreioHabilitado({
      DEV: false,
      MODE: "production",
      VITE_ENABLE_DELIVERY_SIMULATOR: "true",
    }),
    false,
  );
  assert.equal(
    simuladorRastreioHabilitado({
      DEV: false,
      MODE: "staging",
      VITE_ENABLE_DELIVERY_SIMULATOR: "true",
    }),
    true,
  );
});
