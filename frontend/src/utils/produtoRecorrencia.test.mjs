import assert from "node:assert/strict";
import test from "node:test";

import {
  alterarQuantidadeDoses,
  criarRegraRecorrencia,
  montarProtocolosRecorrenciaPayload,
  normalizarProtocolosRecorrencia,
  TIPO_PROTOCOLO_DOSES,
  validarProtocolosRecorrencia,
} from "./produtoRecorrencia.js";

test("cria protocolo com dose 1 fixa no dia da venda", () => {
  const regra = criarRegraRecorrencia(TIPO_PROTOCOLO_DOSES);
  assert.equal(regra.doses[0].dias_desde_inicio, "0");
  assert.equal(regra.oferecer_novo_protocolo, false);
  assert.equal(regra.reiniciar_apos_dias, "");
});

test("permite configurar doses em dias contados desde o início", () => {
  let regra = criarRegraRecorrencia(TIPO_PROTOCOLO_DOSES);
  regra = alterarQuantidadeDoses(regra, 3);
  regra.doses[1].dias_desde_inicio = "14";
  regra.doses[2].dias_desde_inicio = "21";
  regra.oferecer_novo_protocolo = true;
  regra.reiniciar_apos_dias = "180";

  assert.equal(validarProtocolosRecorrencia([regra]), null);
  assert.deepEqual(
    montarProtocolosRecorrenciaPayload([regra])[0].doses.map(
      ({ numero_dose, dias_desde_inicio }) => ({ numero_dose, dias_desde_inicio }),
    ),
    [
      { numero_dose: 1, dias_desde_inicio: 0 },
      { numero_dose: 2, dias_desde_inicio: 14 },
      { numero_dose: 3, dias_desde_inicio: 21 },
    ],
  );
  assert.equal(montarProtocolosRecorrenciaPayload([regra])[0].reiniciar_apos_dias, 180);
});

test("converte cadastro antigo sem perder a recorrência", () => {
  const regras = normalizarProtocolosRecorrencia({
    tem_recorrencia: true,
    intervalo_dias: 21,
    numero_doses: 3,
    especie_compativel: "dog",
  });
  assert.deepEqual(
    regras[0].doses.map((dose) => Number(dose.dias_desde_inicio)),
    [0, 21, 42],
  );
});

test("rejeita doses fora de ordem e retorno sem prazo", () => {
  const regra = criarRegraRecorrencia(TIPO_PROTOCOLO_DOSES);
  regra.doses[1].dias_desde_inicio = "0";
  assert.match(validarProtocolosRecorrencia([regra]), /dias crescentes/);

  regra.doses[1].dias_desde_inicio = "14";
  regra.oferecer_novo_protocolo = true;
  assert.match(validarProtocolosRecorrencia([regra]), /Informe em quantos dias/);
});
