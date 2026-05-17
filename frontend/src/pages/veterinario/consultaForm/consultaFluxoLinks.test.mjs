import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAgendarRetornoConsultaLink,
  buildInternacaoConsultaLink,
} from "./consultaFluxoLinks.js";

test("buildAgendarRetornoConsultaLink monta deep link com pet, tutor, consulta e retorno", () => {
  const link = buildAgendarRetornoConsultaLink({
    contextoConsultaParams: "pet_id=1150&consulta_id=16&tutor_id=77&tutor_nome=Lucas+Guerra",
    form: {
      diagnostico: "Inflamacao no intestino",
      tratamento: "Cuidados em casa",
    },
    consultaIdAtual: 16,
  });
  const url = new URL(link, "https://mlprohub.test");

  assert.equal(url.pathname, "/veterinario/agenda");
  assert.equal(url.searchParams.get("abrir_novo"), "1");
  assert.equal(url.searchParams.get("novo_pet_id"), "1150");
  assert.equal(url.searchParams.get("consulta_id"), "16");
  assert.equal(url.searchParams.get("consulta_origem_id"), "16");
  assert.equal(url.searchParams.get("tutor_id"), "77");
  assert.equal(url.searchParams.get("tutor_nome"), "Lucas Guerra");
  assert.equal(url.searchParams.get("tipo"), "retorno");
  assert.equal(url.searchParams.get("motivo"), "Retorno - Inflamacao no intestino");
  assert.equal(url.searchParams.get("return_to"), "/veterinario/consultas/16?etapa=2");
});

test("buildAgendarRetornoConsultaLink devolve null sem pet salvo", () => {
  assert.equal(
    buildAgendarRetornoConsultaLink({
      contextoConsultaParams: "consulta_id=16&tutor_id=77",
      form: {},
      consultaIdAtual: 16,
    }),
    null,
  );
});

test("buildInternacaoConsultaLink monta deep link para internacao vinculada a consulta", () => {
  const link = buildInternacaoConsultaLink({
    contextoConsultaParams: "pet_id=1150&consulta_id=16&tutor_id=77&tutor_nome=Lucas+Guerra",
    form: { diagnostico: "Inflamacao no intestino" },
    consultaIdAtual: 16,
  });
  const url = new URL(link, "https://mlprohub.test");

  assert.equal(url.pathname, "/veterinario/internacoes");
  assert.equal(url.searchParams.get("abrir_nova"), "1");
  assert.equal(url.searchParams.get("novo_pet_id"), "1150");
  assert.equal(url.searchParams.get("consulta_id"), "16");
  assert.equal(url.searchParams.get("tutor_id"), "77");
  assert.equal(url.searchParams.get("tutor_nome"), "Lucas Guerra");
  assert.equal(url.searchParams.get("motivo"), "Internacao apos consulta #16 - Inflamacao no intestino");
});
