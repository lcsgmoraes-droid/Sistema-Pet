import assert from "node:assert/strict";
import { test } from "node:test";
import {
  LINKS_META,
  PASSOS_NA_META,
  PASSOS_NO_SISTEMA,
  passoDoErro,
  passosConcluidos,
  resumoDoVinculo,
} from "./guiaMeta.js";

test("os passos do guia vão de 1 a 9 sem buraco e os links existem", () => {
  const numeros = [
    ...PASSOS_NA_META.map((_, indice) => indice + 1),
    ...PASSOS_NO_SISTEMA.map((passo) => passo.numero),
  ];
  assert.deepEqual(numeros, [1, 2, 3, 4, 5, 6, 7, 8, 9]);
  for (const passo of PASSOS_NA_META) {
    for (const link of passo.links) assert.ok(LINKS_META[link.href], link.href);
  }
});

test("resumoDoVinculo conta a situação em palavras, nunca só em cor", () => {
  assert.equal(resumoDoVinculo({ status: {} }).texto, "Não configurado");
  assert.equal(resumoDoVinculo({ status: { codigo: "aguardando_teste" } }).texto, "Falta testar");
  assert.equal(resumoDoVinculo({ status: { codigo: "erro" } }).tom, "erro");
  assert.equal(resumoDoVinculo({ status: { codigo: "conectado" } }).texto, "Conectado");
  assert.equal(
    resumoDoVinculo({ ativo: true, status: { codigo: "conectado" } }).texto,
    "WhatsApp oficial ativo",
  );
});

test("passoDoErro leva o usuário ao passo certo do guia", () => {
  assert.equal(passoDoErro("token"), "token");
  assert.equal(passoDoErro("ids"), "numero");
  assert.equal(passoDoErro(null), null);
});

test("passosConcluidos só marca credenciais quando os quatro dados existem", () => {
  const base = { waba_id: "1", phone_number_id: "2", tem_token: true, tem_app_secret: false };
  assert.equal(passosConcluidos({ credenciais: base }).credenciais, false);
  assert.equal(
    passosConcluidos({ credenciais: { ...base, tem_app_secret: true } }).credenciais,
    true,
  );
  const feitos = passosConcluidos({
    credenciais: base,
    status: { codigo: "conectado", ultimo_webhook_em: "2026-10-26T10:00:00" },
    ativo: true,
  });
  assert.deepEqual([feitos.webhook, feitos.testar, feitos.ativar], [true, true, true]);
});
