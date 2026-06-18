import assert from "node:assert/strict";
import test from "node:test";

import {
  RASCUNHO_SALVO_ACOES,
  buildMensagemRascunhoSalvo,
  listarAcoesRascunhoSalvo,
} from "./consultaRascunhoFeedback.js";

test("buildMensagemRascunhoSalvo informa quando o rascunho ainda pode ser finalizado depois", () => {
  assert.equal(
    buildMensagemRascunhoSalvo({ etapa: 2, totalEtapas: 3 }),
    "Rascunho salvo com sucesso. Voce pode finalizar quando quiser.",
  );
});

test("listarAcoesRascunhoSalvo oferece continuar, topo e lista de consultas", () => {
  assert.deepEqual(
    listarAcoesRascunhoSalvo().map((acao) => acao.id),
    [RASCUNHO_SALVO_ACOES.CONTINUAR, RASCUNHO_SALVO_ACOES.TOPO, RASCUNHO_SALVO_ACOES.LISTA],
  );
});
