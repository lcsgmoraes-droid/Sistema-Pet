import assert from "node:assert/strict";
import {
  formatInitialAccessCredentials,
  resolveTenantLoginReference,
} from "./usuarioAcessoInicial.js";

assert.equal(
  resolveTenantLoginReference({
    tenant: { name: "Pet Feliz Demo", login_name: " Acesso Pet Feliz " },
  }),
  "Acesso Pet Feliz",
);
assert.equal(
  resolveTenantLoginReference(
    null,
    JSON.stringify({ name: "Loja do Bairro", login_name: "Equipe Bairro" }),
  ),
  "Equipe Bairro",
);
assert.equal(resolveTenantLoginReference(null, { nome: "Pet Center" }), "Pet Center");
assert.equal(resolveTenantLoginReference(null, "nao-e-json"), "");

assert.equal(
  formatInitialAccessCredentials({
    tenant: "Vira Latas",
    loginPhone: "18997401641",
    password: "Senha Inicial 123",
  }),
  [
    "Acesso ao CorePet",
    "Celular: 18997401641",
    "Senha inicial: Senha Inicial 123",
    "Login: https://corepet.com.br/login",
  ].join("\n"),
);
assert.equal(
  formatInitialAccessCredentials({
    tenant: "Pet Feliz Demo",
    username: "maria.silva",
    password: "Senha Inicial 123",
  }),
  [
    "Acesso ao CorePet",
    "Loja: Pet Feliz Demo",
    "Nome de usuario: maria.silva",
    "Senha inicial: Senha Inicial 123",
    "Login: https://corepet.com.br/login",
  ].join("\n"),
);
assert.equal(formatInitialAccessCredentials(null), "");

console.log("usuarioAcessoInicial tests passed");
