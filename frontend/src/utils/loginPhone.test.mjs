import assert from "node:assert/strict";
import test from "node:test";
import {
  formatBrazilianLoginPhone,
  isBrazilianMobileLogin,
  looksLikePhoneLoginInput,
  normalizeBrazilianLoginPhone,
} from "./loginPhone.js";

test("normaliza celular brasileiro com ou sem codigo do pais", () => {
  assert.equal(normalizeBrazilianLoginPhone("(18) 99740-1641"), "18997401641");
  assert.equal(normalizeBrazilianLoginPhone("+55 18 99740-1641"), "18997401641");
});

test("reconhece somente celular completo com DDD", () => {
  assert.equal(isBrazilianMobileLogin("18997401641"), true);
  assert.equal(isBrazilianMobileLogin("(18) 99740-1641"), true);
  assert.equal(isBrazilianMobileLogin("1832241234"), false);
  assert.equal(isBrazilianMobileLogin("maria.silva"), false);
  assert.equal(looksLikePhoneLoginInput("18997"), true);
  assert.equal(looksLikePhoneLoginInput("maria.silva"), false);
});

test("formata celular para exibicao", () => {
  assert.equal(formatBrazilianLoginPhone("18997401641"), "(18) 99740-1641");
});
