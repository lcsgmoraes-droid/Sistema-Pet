import assert from "node:assert/strict";
import { test } from "node:test";
import {
  agruparPorGrupo,
  descreverAlteracao,
  modulosAlterados,
  modulosAtivos,
  modulosDoPlano,
  nomesDosModulosAtivos,
  rotuloDoStatus,
  rotuloDoUltimoAcesso,
  situacaoDoUsuario,
  totaisDasLojas,
} from "./opsLojasUtils.js";

const modulo = (codigo, ativo, origens = []) => ({ codigo, ativo, origens });

test("agruparPorGrupo ordena os grupos e deixa 'sem agrupamento' por último", () => {
  const lojas = [
    { id: "1", nome: "B1", grupo: { id: 2, nome: "Beta" } },
    { id: "2", nome: "Solta", grupo: null },
    { id: "3", nome: "A1", grupo: { id: 1, nome: "Alfa" } },
    { id: "4", nome: "A2", grupo: { id: 1, nome: "Alfa" } },
  ];

  const grupos = agruparPorGrupo(lojas);

  assert.deepEqual(
    grupos.map((grupo) => [grupo.nome, grupo.lojas.length]),
    [
      ["Alfa", 2],
      ["Beta", 1],
      ["Sem agrupamento", 1],
    ],
  );
});

test("modulosAlterados acha o módulo que foi ligado ou desligado", () => {
  assert.deepEqual(modulosAlterados(["a"], ["a", "b"]), { modulo: "b", ativar: true });
  assert.deepEqual(modulosAlterados(["a", "b"], ["a"]), { modulo: "b", ativar: false });
  assert.equal(modulosAlterados(["a"], ["a"]), null);
});

test("módulos que vêm do plano ou do teste não contam como ativação manual", () => {
  const loja = {
    modulos: [
      modulo("crm", true, ["manual"]),
      modulo("rh", true, ["plano"]),
      modulo("fiscal", true, ["trial", "assinatura"]),
      modulo("bling", false, []),
    ],
  };

  assert.deepEqual(modulosAtivos(loja), ["crm", "rh", "fiscal"]);
  assert.deepEqual(modulosDoPlano(loja), ["rh"]);
});

test("nomesDosModulosAtivos usa o nome amigável e ordena", () => {
  const loja = { modulos: [modulo("rh", true), modulo("compras", true), modulo("bling", false)] };
  const info = { rh: { nome: "Recursos Humanos" }, compras: { nome: "Compras e Entrada XML" } };

  assert.deepEqual(nomesDosModulosAtivos(loja, info), [
    "Compras e Entrada XML",
    "Recursos Humanos",
  ]);
});

test("descreverAlteracao traduz módulo e campos da loja e troca vazio por traço", () => {
  const moduloAlterado = descreverAlteracao(
    { categoria: "modulo", campo: "crm", antes: "inativo", depois: "ativo" },
    { crm: { nome: "CRM" } },
  );
  assert.deepEqual(moduloAlterado, { titulo: "Módulo CRM", antes: "Inativo", depois: "Ativo" });

  const comercial = descreverAlteracao({
    categoria: "comercial",
    campo: "billing_status",
    antes: null,
    depois: "paid",
  });
  assert.deepEqual(comercial, { titulo: "Situação da cobrança", antes: "—", depois: "Paid" });
});

test("rotuloDoUltimoAcesso fala em dias e trata quem nunca entrou", () => {
  const agora = new Date("2026-10-28T12:00:00Z");

  assert.equal(rotuloDoUltimoAcesso(null, agora), "Nunca acessou");
  assert.equal(rotuloDoUltimoAcesso("2026-10-28T08:00:00Z", agora), "Hoje");
  assert.equal(rotuloDoUltimoAcesso("2026-10-27T08:00:00Z", agora), "Ontem");
  assert.equal(rotuloDoUltimoAcesso("2026-10-18T08:00:00Z", agora), "Há 10 dias");
});

test("situacaoDoUsuario diz em palavras por que o usuário não está ativo", () => {
  assert.equal(situacaoDoUsuario({ ativo: true }), "Ativo");
  assert.equal(situacaoDoUsuario({ ativo: false, acesso_ativo_na_loja: true }), "Usuário inativo");
  assert.equal(
    situacaoDoUsuario({ ativo: false, acesso_ativo_na_loja: false }),
    "Sem acesso a esta loja",
  );
});

test("totaisDasLojas conta lojas, usuários e lojas sem usuário ativo", () => {
  const lojas = [
    { usuarios: { total: 3, ativos: 2 } },
    { usuarios: { total: 1, ativos: 0 } },
    { usuarios: { total: 0, ativos: 0 } },
  ];

  assert.deepEqual(totaisDasLojas(lojas), { lojas: 3, usuarios: 4, semUsuarioAtivo: 2 });
  assert.equal(rotuloDoStatus("trial"), "Em teste");
});
