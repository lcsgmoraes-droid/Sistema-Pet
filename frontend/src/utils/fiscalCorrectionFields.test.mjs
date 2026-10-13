import assert from "node:assert/strict";
import test from "node:test";
import { agruparPendenciasFiscais, camposFiscaisAlterados } from "./fiscalCorrectionFields.mjs";

const campos = { ncm: {}, cfop: {}, pis_cst: {}, cofins_cst: {} };

test("rejeição 778 abre o NCM do item 23 mesmo com pré-validação aprovada", () => {
  const validacao = {
    pode_emitir: true,
    bloqueios: [],
    correcoes: [],
    diagnostico_rejeicao: {
      codigo: "778",
      correcoes: [
        {
          produto_id: 9405,
          item_id: 123,
          item_numero: 23,
          campo: "ncm",
          valor_atual: "29007158",
          historico: true,
        },
      ],
    },
  };
  const { produtos, gerais } = agruparPendenciasFiscais(validacao, campos);
  assert.equal(produtos.length, 1);
  assert.equal(produtos[0].itemId, 123);
  assert.equal(produtos[0].itemNumero, 23);
  assert.equal(produtos[0].pendencias[0].valor_atual, "29007158");
  assert.deepEqual(gerais, []);
  assert.equal(validacao.pode_emitir, true);
  assert.deepEqual(validacao.correcoes, []);
});

test("mescla orientação da rejeição com sugestão existente sem duplicar o campo", () => {
  const comum = { produto_id: 9405, item_numero: 23, campo: "ncm" };
  const { produtos } = agruparPendenciasFiscais(
    {
      correcoes: [
        {
          ...comum,
          valor_sugerido: "40151200",
          confianca: "baixa",
          preenchimento_automatico: false,
        },
      ],
      diagnostico_rejeicao: {
        correcoes: [{ ...comum, item_id: 123, historico: true, mensagem: "NCM inexistente" }],
      },
    },
    campos,
  );
  assert.equal(produtos[0].pendencias.length, 1);
  assert.equal(produtos[0].itemId, 123);
  assert.equal(produtos[0].pendencias[0].valor_sugerido, "40151200");
  assert.equal(produtos[0].pendencias[0].preenchimento_automatico, false);
  assert.equal(produtos[0].pendencias[0].mensagem, "NCM inexistente");
});

test("itens do mesmo produto em lotes diferentes mantêm formulários separados", () => {
  const { produtos } = agruparPendenciasFiscais(
    {
      bloqueios: [
        { produto_id: 9405, item_id: 123, item_numero: 23, lote_id: 1, campo: "ncm" },
        { produto_id: 9405, item_id: 124, item_numero: 24, lote_id: 2, campo: "ncm" },
      ],
    },
    campos,
  );
  assert.equal(produtos.length, 2);
  assert.notEqual(produtos[0].chave, produtos[1].chave);
});

test("envia somente campos corrigidos e traduz nomes PIS/COFINS do editor", () => {
  const produto = { pendencias: [{ campo: "ncm" }, { campo: "pis_cst" }, { campo: "cofins_cst" }] };
  const original = { ncm: "29007158", pis_cst: "01", cofins_cst: "01", cfop: "5102" };
  const fiscal = { ...original, ncm: "40151200", pis_cst: "07", cofins_cst: "07", cfop: "6102" };
  assert.deepEqual(camposFiscaisAlterados(produto, fiscal, original), {
    ncm: "40151200",
    cfop: "6102",
    cst_pis: "07",
    cst_cofins: "07",
  });
  assert.deepEqual(camposFiscaisAlterados(produto, original, original), {});
});

test("salva CEST aplicado pela consulta mesmo quando somente NCM foi rejeitado", () => {
  const produto = { pendencias: [{ campo: "ncm" }] };
  const original = { ncm: "29007158", cest: "", cfop: "5102" };
  const fiscal = { ...original, ncm: "40151200", cest: "1301600", campo_desconhecido: "ignorar" };
  assert.deepEqual(camposFiscaisAlterados(produto, fiscal, original), {
    ncm: "40151200",
    cest: "1301600",
  });
  assert.deepEqual(
    camposFiscaisAlterados(produto, { ...original, cest: "" }, { ...original, cest: "1301600" }),
    { cest: "" },
  );
});

test("pendência sem campo editável continua na orientação geral", () => {
  const pendencia = { campo: "certificado", mensagem: "Confira o certificado" };
  assert.deepEqual(agruparPendenciasFiscais({ bloqueios: [pendencia] }, campos), {
    produtos: [],
    gerais: [pendencia],
  });
});
