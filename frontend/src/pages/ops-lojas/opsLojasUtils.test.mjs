import assert from "node:assert/strict";
import { test } from "node:test";
import {
  agruparPorGrupo,
  descreverAlteracao,
  modulosAlterados,
  modulosAtivos,
  modulosDoPlano,
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

test("descreverAlteracao traduz módulo e campos da loja e troca vazio por traço", () => {
  const modulo = descreverAlteracao(
    { categoria: "modulo", campo: "crm", antes: "inativo", depois: "ativo" },
    { crm: { nome: "CRM" } },
  );
  assert.deepEqual(modulo, { titulo: "Módulo CRM", antes: "Inativo", depois: "Ativo" });

  const comercial = descreverAlteracao({
    categoria: "comercial",
    campo: "billing_status",
    antes: null,
    depois: "paid",
  });
  assert.deepEqual(comercial, { titulo: "Situação da cobrança", antes: "—", depois: "Paid" });
});
