import assert from "node:assert/strict";
import test from "node:test";
import { normalizarAcertoEntregador, validarAcertoEntregador } from "./entregadorAcerto.js";

test("entregador sem acerto pode ser salvo e limpa os dias antigos", () => {
  const dados = {
    is_entregador: true,
    tipo_acerto_entrega: "",
    dia_mes_acerto: 15,
    dia_semana_acerto: 3,
  };
  assert.equal(validarAcertoEntregador(dados), null);
  assert.deepEqual(normalizarAcertoEntregador(dados), {
    ...dados,
    tipo_acerto_entrega: null,
    dia_mes_acerto: null,
    dia_semana_acerto: null,
  });
});

test("acertos com periodicidade continuam exigindo o dia correto", () => {
  for (const dia of ["", 0, 8, 2.5]) {
    assert.ok(
      validarAcertoEntregador({
        is_entregador: true,
        tipo_acerto_entrega: "semanal",
        dia_semana_acerto: dia,
      }),
    );
  }
  for (const dia of ["", 0, 29, 2.5]) {
    assert.ok(
      validarAcertoEntregador({
        is_entregador: true,
        tipo_acerto_entrega: "mensal",
        dia_mes_acerto: dia,
      }),
    );
  }
  assert.equal(
    validarAcertoEntregador({ is_entregador: true, tipo_acerto_entrega: "quinzenal" }),
    null,
  );
  assert.equal(
    validarAcertoEntregador({
      is_entregador: true,
      tipo_acerto_entrega: "semanal",
      dia_semana_acerto: "7",
    }),
    null,
  );
  assert.equal(
    normalizarAcertoEntregador({
      tipo_acerto_entrega: "mensal",
      dia_mes_acerto: "28",
      dia_semana_acerto: 1,
    }).dia_semana_acerto,
    null,
  );
});
