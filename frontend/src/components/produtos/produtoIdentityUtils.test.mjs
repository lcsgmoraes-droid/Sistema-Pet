import assert from "node:assert/strict";
import { test } from "node:test";
import {
  campoPreservadoNaFusao,
  podeAplicarFusao,
  separarAliasesSku,
} from "./produtoIdentityUtils.js";

test("aliases comerciais preservam pontuação e eliminam duplicatas sem inventar códigos", () => {
  assert.deepEqual(separarAliasesSku(" OF-WCWX-M80J, PCTPMD00003\n of-wcwx-m80j ; ABC.1\nABC1"), [
    "of-wcwx-m80j",
    "PCTPMD00003",
    "ABC.1",
    "ABC1",
  ]);
  assert.deepEqual(separarAliasesSku(""), []);
});

test("manter principal protege identidade, custo e preços mesmo com decisão contrária", () => {
  for (const campo of [
    "codigo",
    "nome",
    "unidade",
    "codigo_barras",
    "codigos_barras_alternativos",
    "preco_custo",
    "preco_ecommerce_promo",
    "promocao_inicio",
  ]) {
    assert.equal(campoPreservadoNaFusao(campo, "manter_principal"), true, campo);
    assert.equal(campoPreservadoNaFusao(campo, "somar"), false, campo);
  }
  assert.equal(campoPreservadoNaFusao("descricao_completa", "manter_principal"), false);
});

test("a fusão exige revisão atual, consentimento Bling e nenhuma fila ativa", () => {
  const state = {
    preview: { preview_token: "a".repeat(64), conflito_bling: true, filas_pendentes: 0 },
    previewAtual: true,
    confirmado: true,
    preservarBling: true,
    aliases: ["OF-WCWX-M80J"],
    ocupado: false,
    estrategia: "manter_principal",
    observacao: "Contagem física conferida, duplicado já incluído.",
  };
  assert.equal(podeAplicarFusao(state), true);
  for (const changed of [
    { previewAtual: false },
    { confirmado: false },
    { preservarBling: false },
    { ocupado: true },
    { observacao: "curto" },
    { preview: { ...state.preview, filas_pendentes: 1 } },
    { preview: null },
    { aliases: Array.from({ length: 21 }, (_, i) => String(i)) },
    { aliases: ["x".repeat(101)] },
  ]) {
    assert.equal(podeAplicarFusao({ ...state, ...changed }), false);
  }
  assert.equal(
    podeAplicarFusao({ ...state, estrategia: "somar", aliases: [], observacao: "" }),
    true,
  );
  assert.equal(podeAplicarFusao({ ...state, estrategia: "somar", observacao: "" }), false);
});
