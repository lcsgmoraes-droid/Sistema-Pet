import assert from "node:assert/strict";
import test from "node:test";
import { dataHoraIfoodParaFormulario, serializarDataHoraIfood } from "./ifoodProdutoDates.js";

test("preserva o horário local da promoção iFood ao salvar e reabrir", () => {
  const horarioLocal = "2026-10-19T18:00";
  const iso = serializarDataHoraIfood(horarioLocal);
  assert.equal(iso, new Date(2026, 9, 19, 18, 0).toISOString());
  assert.equal(dataHoraIfoodParaFormulario(iso), horarioLocal);
});

test("preserva o instante recebido com offset e datas antigas UTC", () => {
  const recebido = "2026-10-19T18:00:00-03:00";
  assert.equal(serializarDataHoraIfood(recebido), "2026-10-19T21:00:00.000Z");
  assert.equal(
    dataHoraIfoodParaFormulario("2026-10-19T21:00:00"),
    dataHoraIfoodParaFormulario(recebido),
  );
});

test("datas ausentes ou inválidas continuam pendências do canal", () => {
  assert.equal(serializarDataHoraIfood(""), null);
  assert.equal(serializarDataHoraIfood("invalida"), null);
  assert.equal(dataHoraIfoodParaFormulario(null), "");
  assert.equal(dataHoraIfoodParaFormulario("invalida"), "");
});
