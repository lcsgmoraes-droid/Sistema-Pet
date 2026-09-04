import assert from "node:assert/strict";
import test from "node:test";

import {
  protocoloCompativelComPet,
  sugerirProtocoloRecorrencia,
} from "./pdvProtocolosRecorrencia.js";
import { montarItensVendaPayload } from "./pdvVendaPayload.js";

const protocolos = [
  { id: 10, especie_compativel: "dog", fase_vida: "puppy" },
  { id: 20, especie_compativel: "dog", fase_vida: "adult" },
];

test("sugere protocolo de filhote pela espécie e idade", () => {
  const pet = { especie: "Cão", idade_aproximada: 5 };
  assert.equal(sugerirProtocoloRecorrencia(protocolos, pet), 10);
  assert.equal(protocoloCompativelComPet(protocolos[1], pet), false);
});

test("sugere protocolo adulto e não decide quando a idade falta", () => {
  assert.equal(
    sugerirProtocoloRecorrencia(protocolos, { especie: "canino", idade_aproximada: 24 }),
    20,
  );
  assert.equal(sugerirProtocoloRecorrencia(protocolos, { especie: "canino" }), null);
});

test("grava quando o operador escolhe não iniciar a recorrência", () => {
  const [item] = montarItensVendaPayload({
    itens: [
      {
        tipo: "produto",
        produto_id: 10,
        quantidade: 1,
        preco_unitario: 50,
        subtotal: 50,
        protocolo_recorrencia_id: null,
        ignorar_recorrencia: true,
      },
    ],
  });

  assert.equal(item.protocolo_recorrencia_id, null);
  assert.equal(item.ignorar_recorrencia, true);
});
