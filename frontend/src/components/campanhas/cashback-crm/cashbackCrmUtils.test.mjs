import assert from "node:assert/strict";
import { test } from "node:test";
import { dataCashback, mensagemCashback, registrarEAbrirWhatsApp } from "./cashbackCrmUtils.js";

test("mensagem personaliza apenas variáveis conhecidas e formata saldo brasileiro", () => {
  assert.equal(
    mensagemCashback("Oi, {nome}! {saldo} disponível. {nome} {outro}", {
      nome: "Ana Maria",
      saldo_cashback: 1234.5,
    }),
    "Oi, Ana! R$ 1.234,50 disponível. Ana {outro}",
  );
  assert.equal(mensagemCashback("{nome}: {saldo}", {}), "cliente: R$ 0,00");
});

test("data de retorno não muda de dia ao tratar data sem horário", () => {
  assert.equal(dataCashback("2026-10-19"), "19/10/2026");
  assert.equal(dataCashback(null), "—");
});

test("popup bloqueado não registra contato", async () => {
  let registros = 0;
  await assert.rejects(
    registrarEAbrirWhatsApp({
      abrirAba: () => null,
      registrar: async () => {
        registros += 1;
      },
    }),
    /bloqueou/,
  );
  assert.equal(registros, 0);
});

test("conversa só navega depois do histórico persistido", async () => {
  const eventos = [];
  const aba = {
    opener: {},
    location: { replace: (url) => eventos.push(url) },
    close: () => eventos.push("fechou"),
  };
  await registrarEAbrirWhatsApp({
    abrirAba: () => {
      eventos.push("abriu");
      return aba;
    },
    registrar: async () => {
      eventos.push("registrou");
      return { whatsapp_url: "https://wa.me/5518999999999?text=Oi" };
    },
  });
  assert.deepEqual(eventos, ["abriu", "registrou", "https://wa.me/5518999999999?text=Oi"]);
  assert.equal(aba.opener, null);
});

test("falha ao registrar fecha a aba e não navega", async () => {
  const eventos = [];
  await assert.rejects(
    registrarEAbrirWhatsApp({
      abrirAba: () => ({
        location: { replace: () => eventos.push("navegou") },
        close: () => eventos.push("fechou"),
      }),
      registrar: async () => {
        throw new Error("Falha no histórico");
      },
    }),
    /Falha no histórico/,
  );
  assert.deepEqual(eventos, ["fechou"]);
});

test("link inesperado fecha a aba e não é aberto", async () => {
  const eventos = [];
  await assert.rejects(
    registrarEAbrirWhatsApp({
      abrirAba: () => ({
        location: { replace: () => eventos.push("navegou") },
        close: () => eventos.push("fechou"),
      }),
      registrar: async () => ({ whatsapp_url: "https://example.com" }),
    }),
    /inválido/,
  );
  assert.deepEqual(eventos, ["fechou"]);
});
