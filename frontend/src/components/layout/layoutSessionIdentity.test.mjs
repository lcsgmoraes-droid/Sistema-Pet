import assert from "node:assert/strict";
import test from "node:test";

import { resolveLayoutSessionIdentity } from "./layoutSessionIdentity.js";

test("mostra a identificacao da loja e o usuario logado", () => {
  const identity = resolveLayoutSessionIdentity({
    name: "Jefferson",
    username: "jefferson",
    email: "jefferson@exemplo.com",
    tenant: {
      name: "Casa de Racao Vira Lata",
      login_name: "viralatas",
    },
  });

  assert.equal(identity.tenantLabel, "viralatas");
  assert.equal(identity.userLabel, "jefferson");
  assert.equal(identity.avatarInitial, "J");
});

test("formata celular de acesso e usa o nome da loja como fallback", () => {
  const identity = resolveLayoutSessionIdentity({
    login_phone: "18997401641",
    tenant: { name: "Casa de Racao Vira Lata" },
  });

  assert.equal(identity.tenantLabel, "Casa de Racao Vira Lata");
  assert.equal(identity.userLabel, "(18) 99740-1641");
});

test("mantem email para contas antigas e evita valores vazios", () => {
  const identity = resolveLayoutSessionIdentity({
    email: "  gerente@exemplo.com  ",
    tenant: { login_name: " ", name: " Aumigos Pet Shop " },
  });

  assert.equal(identity.tenantLabel, "Aumigos Pet Shop");
  assert.equal(identity.userLabel, "gerente@exemplo.com");
  assert.equal(identity.avatarInitial, "G");
});
