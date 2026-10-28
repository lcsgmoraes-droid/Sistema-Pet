import assert from "node:assert/strict";
import { test } from "node:test";
import {
  checarSenhaNova,
  descreverAlteracao,
  formatarReaisDeCentavos,
  nomesDosModulosAtivos,
  ordenarLojas,
  origensEmTexto,
  podeDesligar,
  rotuloDoStatus,
  rotuloDoUltimoAcesso,
  situacaoDoUsuario,
  totaisDasLojas,
} from "./formatadores.js";

const catalogo = [
  { codigo: "rh", nome: "Recursos humanos" },
  { codigo: "compras", nome: "Compras e entrada XML" },
];

test("rotuloDoUltimoAcesso fala em dias e trata quem nunca entrou", () => {
  const agora = new Date("2026-10-28T12:00:00Z");

  assert.equal(rotuloDoUltimoAcesso(null, agora), "Nunca acessou");
  assert.equal(rotuloDoUltimoAcesso("2026-10-28T08:00:00Z", agora), "Hoje");
  assert.equal(rotuloDoUltimoAcesso("2026-10-27T08:00:00Z", agora), "Ontem");
  assert.equal(rotuloDoUltimoAcesso("2026-10-18T08:00:00Z", agora), "Há 10 dias");
});

test("podeDesligar: só o que foi ativado manualmente ou por assinatura", () => {
  assert.equal(podeDesligar({ ativo: true, origens: ["manual"] }), true);
  assert.equal(podeDesligar({ ativo: true, origens: ["plano"] }), false);
  assert.equal(podeDesligar({ ativo: true, origens: ["plano", "manual"] }), true);
  assert.equal(podeDesligar({ ativo: false, origens: [] }), true);
});

test("origensEmTexto traduz as origens", () => {
  assert.equal(origensEmTexto(["manual", "trial"]), "Ativado manualmente · Teste grátis");
});

test("nomesDosModulosAtivos usa o nome do catálogo e ordena", () => {
  const loja = {
    modulos: [
      { codigo: "rh", ativo: true },
      { codigo: "compras", ativo: true },
      { codigo: "bling", ativo: false },
    ],
  };

  assert.deepEqual(nomesDosModulosAtivos(loja, catalogo), ["Compras e entrada XML", "Recursos humanos"]);
});

test("ordenarLojas junta o agrupamento e deixa quem não tem grupo no fim", () => {
  const lojas = [
    { nome: "Solta", grupo: null },
    { nome: "B", grupo: { nome: "Beta" } },
    { nome: "A2", grupo: { nome: "Alfa" } },
    { nome: "A1", grupo: { nome: "Alfa" } },
  ];

  assert.deepEqual(
    ordenarLojas(lojas).map((loja) => loja.nome),
    ["A1", "A2", "B", "Solta"],
  );
});

test("formatadores de valor e status", () => {
  assert.match(formatarReaisDeCentavos(12990), /129,90/);
  assert.equal(formatarReaisDeCentavos(null), "—");
  assert.equal(rotuloDoStatus("trial"), "Em teste");
  assert.equal(rotuloDoStatus(undefined), "Sem status");
});

test("situacaoDoUsuario diz em palavras por que não está ativo", () => {
  assert.equal(situacaoDoUsuario({ ativo: true }), "Ativo");
  assert.equal(situacaoDoUsuario({ ativo: false, acesso_ativo_na_loja: true }), "Usuário inativo");
  assert.equal(situacaoDoUsuario({ ativo: false, acesso_ativo_na_loja: false }), "Sem acesso a esta loja");
});

test("totaisDasLojas conta lojas, usuários e lojas sem usuário ativo", () => {
  const lojas = [
    { usuarios: { total: 3, ativos: 2 } },
    { usuarios: { total: 1, ativos: 0 } },
    { usuarios: { total: 0, ativos: 0 } },
  ];

  assert.deepEqual(totaisDasLojas(lojas), { lojas: 3, usuarios: 4, semUsuarioAtivo: 2 });
});

test("descreverAlteracao traduz módulo e campos e troca vazio por traço", () => {
  assert.deepEqual(
    descreverAlteracao({ categoria: "modulo", campo: "rh", antes: "inativo", depois: "ativo" }, catalogo),
    { titulo: "Módulo Recursos humanos", antes: "Inativo", depois: "Ativo" },
  );
  assert.deepEqual(descreverAlteracao({ categoria: "comercial", campo: "plan", antes: null, depois: "premium" }), {
    titulo: "Plano",
    antes: "—",
    depois: "Premium",
  });
});

test("checarSenhaNova marca cada regra em tempo real", () => {
  const regras = (nova, atual) => checarSenhaNova(nova, atual).map((regra) => regra.ok);

  assert.deepEqual(regras("", "x"), [false, false, false]);
  assert.deepEqual(regras("Frase-longa-de-teste-42", "outra"), [true, true, true]);
  assert.deepEqual(regras("somenteletrasaqui", "outra"), [true, false, true]);
  assert.deepEqual(regras("Frase-longa-de-teste-42", "Frase-longa-de-teste-42"), [true, true, false]);
});
