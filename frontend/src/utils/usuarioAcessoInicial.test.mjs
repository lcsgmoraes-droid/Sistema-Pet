import assert from "node:assert/strict";
import {
  buildInitialAccessCredentials,
  formatInitialAccessCredentials,
  resolveTenantLoginReference,
} from "./usuarioAcessoInicial.js";

assert.equal(
  resolveTenantLoginReference({ tenant: { name: " Pet Feliz Demo " } }),
  "Pet Feliz Demo",
);
assert.equal(
  resolveTenantLoginReference(null, JSON.stringify({ name: "Loja do Bairro" })),
  "Loja do Bairro",
);
assert.equal(resolveTenantLoginReference(null, { nome: "Pet Center" }), "Pet Center");
assert.equal(resolveTenantLoginReference(null, "nao-e-json"), "");

const credentials = buildInitialAccessCredentials({
  tenant: " Pet Feliz Demo ",
  username: " MARIA.SILVA ",
  password: "Senha Inicial 123",
  personName: " Maria Silva ",
});

assert.deepEqual(credentials, {
  tenant: "Pet Feliz Demo",
  username: "maria.silva",
  password: "Senha Inicial 123",
  personName: "Maria Silva",
});
assert.equal(
  buildInitialAccessCredentials({ tenant: "", username: "maria", password: "senha" }),
  null,
);
assert.equal(
  formatInitialAccessCredentials(credentials),
  [
    "Acesso ao CorePet",
    "Loja: Pet Feliz Demo",
    "Nome de usuario: maria.silva",
    "Senha inicial: Senha Inicial 123",
    "Login: https://corepet.com.br/login",
  ].join("\n"),
);

console.log("usuarioAcessoInicial tests passed");
