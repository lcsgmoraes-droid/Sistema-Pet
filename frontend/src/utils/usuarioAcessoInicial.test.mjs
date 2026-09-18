import assert from "node:assert/strict";
import {
  buildInitialAccessCredentials,
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

const credentials = buildInitialAccessCredentials({
  tenant: " Pet Feliz Demo ",
  username: " MARIA.SILVA ",
  password: "Senha Inicial 123",
  personName: " Maria Silva ",
});

assert.deepEqual(credentials, {
  tenant: "Pet Feliz Demo",
  username: "maria.silva",
  loginPhone: "",
  password: "Senha Inicial 123",
  personName: "Maria Silva",
});
assert.equal(
  buildInitialAccessCredentials({ tenant: "", username: "maria", password: "senha" }),
  null,
);

const phoneCredentials = buildInitialAccessCredentials({
  tenant: "Vira Latas",
  loginPhone: "(18) 99740-1641",
  password: "Senha Inicial 123",
  personName: "Maria Silva",
});

assert.deepEqual(phoneCredentials, {
  tenant: "Vira Latas",
  username: "",
  loginPhone: "18997401641",
  password: "Senha Inicial 123",
  personName: "Maria Silva",
});
assert.equal(
  formatInitialAccessCredentials(phoneCredentials),
  [
    "Acesso ao CorePet",
    "Celular: 18997401641",
    "Senha inicial: Senha Inicial 123",
    "Login: https://corepet.com.br/login",
  ].join("\n"),
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
