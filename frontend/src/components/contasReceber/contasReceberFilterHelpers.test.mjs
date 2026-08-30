import assert from "node:assert/strict";

import {
  aplicarPeriodoRapidoContasReceber,
  criarFiltrosContasReceberDaUrl,
  montarParamsFiltrosContasReceber,
  normalizarListaClientes,
} from "./contasReceberFilterHelpers.js";

const url = new URLSearchParams("cliente_id=42&filtro=em_aberto&periodo=todos");
const filtrosUrl = criarFiltrosContasReceberDaUrl(url);
assert.equal(filtrosUrl.cliente_id, "42");
assert.equal(filtrosUrl.status, "em_aberto");
assert.equal(filtrosUrl.data_inicio, "");
assert.equal(filtrosUrl.data_fim, "");

const todosPeriodos = aplicarPeriodoRapidoContasReceber(
  {
    ...filtrosUrl,
    data_inicio: "2026-08-01",
    data_fim: "2026-08-31",
    apenas_vencidas: true,
  },
  "todos",
);
assert.equal(todosPeriodos.data_inicio, "");
assert.equal(todosPeriodos.data_fim, "");
assert.equal(todosPeriodos.apenas_vencidas, false);

const params = montarParamsFiltrosContasReceber(todosPeriodos);
assert.equal(params.get("cliente_id"), "42");
assert.equal(params.get("status"), "em_aberto");

const paramsBusca = montarParamsFiltrosContasReceber(todosPeriodos, "  Maria 1199999  ");
assert.equal(paramsBusca.get("busca"), "Maria 1199999");
assert.equal(paramsBusca.has("numero_venda"), false);

assert.deepEqual(normalizarListaClientes([{ id: 1 }]), [{ id: 1 }]);
assert.deepEqual(normalizarListaClientes({ items: [{ id: 2 }] }), [{ id: 2 }]);
assert.deepEqual(normalizarListaClientes({ clientes: [{ id: 3 }] }), [{ id: 3 }]);
assert.deepEqual(normalizarListaClientes(null), []);

console.log("contasReceberFilterHelpers: ok");
