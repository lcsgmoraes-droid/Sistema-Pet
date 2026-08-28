import assert from "node:assert/strict";
import test from "node:test";

import {
  ALTERAR_PRECO_GRANEL_PADRAO,
  montarCamposAtualizacaoPrecoGranel,
} from "./granelPrecoUtils.js";

test("abre o lancamento de granel preservando o preco atual", () => {
  assert.equal(ALTERAR_PRECO_GRANEL_PADRAO, false);
});

test("mantem o preco do granel quando o usuario nao escolheu alterar", () => {
  assert.deepEqual(
    montarCamposAtualizacaoPrecoGranel({
      deveAlterarPreco: false,
      precoVendaSugerido: 15.2,
    }),
    {
      atualizar_preco_venda_granel: false,
      preco_venda_granel: null,
    },
  );
});

test("envia o novo preco somente apos escolha explicita", () => {
  assert.deepEqual(
    montarCamposAtualizacaoPrecoGranel({
      deveAlterarPreco: true,
      precoVendaSugerido: 15.4455,
    }),
    {
      atualizar_preco_venda_granel: true,
      preco_venda_granel: 15.45,
    },
  );
});

test("nao envia preco invalido mesmo com a opcao marcada", () => {
  assert.deepEqual(
    montarCamposAtualizacaoPrecoGranel({
      deveAlterarPreco: true,
      precoVendaSugerido: 0,
    }),
    {
      atualizar_preco_venda_granel: false,
      preco_venda_granel: null,
    },
  );
});
