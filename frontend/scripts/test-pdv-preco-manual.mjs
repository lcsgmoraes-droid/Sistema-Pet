import assert from "node:assert/strict";

import { recalcularSubtotalItem } from "../src/utils/pdvCarrinhoItensUtils.js";
import { recalcularItemComPrecoEDesconto } from "../src/utils/pdvDescontoItensUtils.js";

const item = {
  produto_id: 6083,
  quantidade: 2,
  preco_unitario: 10,
  desconto_valor: 0,
  desconto_percentual: 0,
  subtotal: 20,
};

const itemComPrecoManual = recalcularItemComPrecoEDesconto(item, {
  produto_id: 6083,
  preco: 8.5,
  tipoDesconto: "valor",
  descontoValor: 1,
  descontoPercentual: 0,
});

assert.equal(itemComPrecoManual.preco_unitario, 8.5);
assert.equal(itemComPrecoManual.subtotal, 16);
assert.equal(itemComPrecoManual.preco_com_desconto, 8);
assert.equal(itemComPrecoManual.desconto_valor, 1);

const itemComQuantidadeAlterada = recalcularSubtotalItem(
  {
    ...itemComPrecoManual,
    tipo_desconto_aplicado: "percentual",
    desconto_percentual: 10,
    desconto_valor: 0,
  },
  2,
);

assert.equal(itemComQuantidadeAlterada.preco_unitario, 8.5);
assert.equal(itemComQuantidadeAlterada.desconto_valor, 1.7);
assert.equal(itemComQuantidadeAlterada.subtotal, 15.3);

console.log("PDV preco manual: OK");
