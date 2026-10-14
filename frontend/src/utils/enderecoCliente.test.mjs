import assert from "node:assert/strict";
import test from "node:test";
import { formatarEnderecoPrincipalCliente } from "./enderecoCliente.js";

test("endereço principal completo inclui número, complemento e localidade", () => {
  assert.equal(
    formatarEnderecoPrincipalCliente({
      endereco: " Rua São João ",
      numero: " 123 ",
      complemento: "Casa A",
      bairro: "Centro",
      cidade: "Andradina",
      estado: "SP",
    }),
    "Rua São João, 123 · Casa A · Centro · Andradina/SP",
  );
});

test("cadastro parcial não cria separadores vazios nem texto undefined", () => {
  assert.equal(formatarEnderecoPrincipalCliente({ endereco: "Rua Principal" }), "Rua Principal");
  assert.equal(
    formatarEnderecoPrincipalCliente({ endereco: "Rua Principal", cidade: "Andradina" }),
    "Rua Principal · Andradina",
  );
});

test("cadastro sem endereço principal não exibe endereço adicional ou linha vazia", () => {
  for (const pessoa of [
    null,
    {},
    { endereco: "  ", numero: "123", cidade: "Andradina" },
    { enderecos_adicionais: [{ endereco: "Rua adicional" }], endereco_entrega: "Outro endereço" },
  ]) {
    assert.equal(formatarEnderecoPrincipalCliente(pessoa), "");
  }
});
