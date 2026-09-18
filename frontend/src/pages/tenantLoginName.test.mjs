import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const registerSource = readFileSync(new URL("./Register.jsx", import.meta.url), "utf8");
const loginSource = readFileSync(new URL("./Login.jsx", import.meta.url), "utf8");
const authSource = readFileSync(new URL("../contexts/AuthContext.jsx", import.meta.url), "utf8");

test("cadastro solicita e envia um nome de acesso separado", () => {
  assert.match(registerSource, /register-nome-acesso/);
  assert.match(registerSource, /nome_acesso: nomeAcesso\.trim\(\)/);
  assert.match(authSource, /nome_acesso/);
});

test("login por usuario pede explicitamente o nome de acesso", () => {
  assert.match(loginSource, /Nome de acesso da loja/);
  assert.match(loginSource, /placeholder="Ex: Vira Latas"/);
});

test("alteracao atualiza o nome de acesso mantido na sessao local", () => {
  assert.match(authSource, /tenant-login-name-updated/);
  assert.match(authSource, /tenant: \{ \.\.\.currentUser\.tenant, login_name: loginName \}/);
});
