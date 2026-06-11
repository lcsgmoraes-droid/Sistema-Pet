import assert from "node:assert/strict";

import {
  buildEmptyClienteAlertaPdv,
  clienteTemAlertasPdv,
  normalizeClienteAlertasPdv,
} from "./clienteAlertasPdv.js";

const normalizados = normalizeClienteAlertasPdv([
  {
    tag: " Preco especial ",
    observacao: " Fazer racao X por R$ 120 ",
    prioridade: "IMPORTANTE",
  },
  { titulo: "", mensagem: "   " },
  { titulo: "Inativo", mensagem: "Nao mostrar", ativo: false },
  "ignorar",
]);

assert.deepEqual(normalizados, [
  {
    titulo: "Preco especial",
    mensagem: "Fazer racao X por R$ 120",
    prioridade: "importante",
    ativo: true,
  },
  {
    titulo: "Inativo",
    mensagem: "Nao mostrar",
    prioridade: "aviso",
    ativo: false,
  },
]);

assert.equal(clienteTemAlertasPdv({ alertas_pdv: normalizados }), true);
assert.equal(
  clienteTemAlertasPdv({
    alertas_pdv: [{ titulo: "Antigo", mensagem: "Nao mostrar", ativo: false }],
  }),
  false,
);

assert.deepEqual(buildEmptyClienteAlertaPdv(), {
  titulo: "",
  mensagem: "",
  prioridade: "aviso",
  ativo: true,
});
