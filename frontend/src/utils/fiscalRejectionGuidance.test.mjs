import assert from "node:assert/strict";
import test from "node:test";
import {
  MENSAGEM_SUPORTE_RESPONSAVEL_TECNICO,
  rejeicaoResponsavelTecnico,
  SUPORTE_FISCAL_COREPET_URL,
} from "./fiscalRejectionGuidance.mjs";

test("rejeição 974 aponta para o fornecedor técnico, não para o CPF da cliente", () => {
  assert.equal(
    rejeicaoResponsavelTecnico({
      codigo: "974",
      motivo: "CNPJ do responsavel tecnico diverge do cadastrado",
    }),
    true,
  );
  assert.equal(
    rejeicaoResponsavelTecnico({
      codigo: "974",
      motivo: "CNPJ do responsável técnico diverge do cadastrado",
    }),
    true,
  );
  assert.equal(
    rejeicaoResponsavelTecnico({ codigo: "999", motivo: "CPF do destinatário inválido" }),
    false,
  );
  assert.equal(
    rejeicaoResponsavelTecnico({ codigo: "999", motivo: "CNPJ do destinatário inválido" }),
    false,
  );
});

test("rejeição do emissor orienta o cliente a procurar o suporte", () => {
  assert.match(MENSAGEM_SUPORTE_RESPONSAVEL_TECNICO, /suporte do CorePet/);
  assert.match(SUPORTE_FISCAL_COREPET_URL, /wa\.me\/5518997401641/);
});
