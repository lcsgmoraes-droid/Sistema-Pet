import assert from "node:assert/strict";
import test from "node:test";
import { rejeicaoResponsavelTecnico } from "./fiscalRejectionGuidance.mjs";

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
