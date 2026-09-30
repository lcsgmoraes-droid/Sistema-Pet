import assert from "node:assert/strict";
import test from "node:test";
import { resolveEmissionState } from "./intnfeEmissionState.mjs";

test("produção habilitada aparece como emissão fiscal ativa", () => {
  const state = resolveEmissionState(
    { emissao_disponivel: true, ambiente: "homologacao" },
    { habilitada: true, ambiente_codigo: 1 },
  );

  assert.equal(state.code, 1);
  assert.equal(state.label, "produção");
  assert.match(state.badge, /Produção ativa/);
  assert.doesNotMatch(state.description, /teste|homologação/);
});

test("homologação habilitada continua identificada como teste", () => {
  const state = resolveEmissionState(null, { habilitada: true, ambiente_codigo: 2 });

  assert.equal(state.enabled, true);
  assert.match(state.badge, /Homologação ativa/);
  assert.match(state.badge, /sem valor fiscal/);
});

test("desativação salva prevalece sobre situação anterior", () => {
  const state = resolveEmissionState(
    { emissao_disponivel: true, ambiente: "producao" },
    { habilitada: false, ambiente_codigo: 1 },
  );

  assert.equal(state.enabled, false);
  assert.equal(state.badge, "Emissão direta desativada");
});

test("situação inicial usa o ambiente informado pelo status da integração", () => {
  const state = resolveEmissionState({ emissao_disponivel: true, ambiente: "producao" }, null);

  assert.equal(state.code, 1);
  assert.equal(state.enabled, true);
});
