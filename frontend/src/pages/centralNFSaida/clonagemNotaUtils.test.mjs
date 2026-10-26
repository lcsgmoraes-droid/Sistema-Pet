import assert from "node:assert/strict";
import test from "node:test";
import {
  atualizarCampoClone,
  atualizarCanalClone,
  canalComercialClone,
  CNPJ_PUBLICO_AMAZON,
  referenciaClonagem,
  totalClonagem,
} from "./clonagemNotaUtils.js";

test("referência da cópia usa origem sem escolher número da nova nota", () => {
  const referencia = referenciaClonagem({ id: 123, provedor: "bling", modelo: "55", numero: 1648 });
  assert.equal(referencia.nfe_id, "123");
  assert.equal(referencia.modelo, 55);
  assert.equal("numero" in referencia, false);
});

test("edição preserva snapshot original e todos os dados fiscais fora do campo alterado", () => {
  const dados = {
    emitente: { cnpj: "123" },
    produtos: [
      { quantidade: 2, valorUnitario: 72.5, valorTotal: 145, impostos: { icms: { cst: "102" } } },
    ],
    pagamentos: [{ formaPagamento: "01", valor: 145 }],
    frete: { modalidade: "9", valor: 0 },
  };
  const atualizado = atualizarCampoClone(dados, "produtos.0.valorUnitario", 60);
  assert.equal(atualizado.produtos[0].valorTotal, 120);
  assert.equal(dados.produtos[0].valorTotal, 145);
  assert.deepEqual(atualizado.produtos[0].impostos, dados.produtos[0].impostos);
  assert.deepEqual(atualizado.pagamentos, dados.pagamentos);
  assert.deepEqual(atualizado.emitente, dados.emitente);
});

test("total inclui IPI e frete da nota uma vez mesmo com frete rateado nos itens", () => {
  const total = totalClonagem({
    produtos: [{ valorTotal: 100, desconto: 5, frete: 10, impostos: { ipi: { valor: 3 } } }],
    frete: { valor: 10 },
  });
  assert.equal(total, 108);
});

test("escolher Amazon altera só presença e intermediador, sem inventar o Seller ID", () => {
  const original = {
    indicadorPresenca: "1",
    emitente: { cnpj: "33590794000140" },
    produtos: [{ valorTotal: 20, impostos: { icms: { cst: "102" } } }],
    informacoesAdicionais: "Pedido QA preservado",
  };
  const copia = atualizarCanalClone(original, "amazon");
  assert.equal(canalComercialClone(copia), "amazon");
  assert.equal(copia.indicadorPresenca, "2");
  assert.deepEqual(copia.intermediador, { cnpj: CNPJ_PUBLICO_AMAZON, identificadorCadastro: "" });
  assert.deepEqual(copia.produtos, original.produtos);
  assert.deepEqual(copia.emitente, original.emitente);
  assert.equal(copia.informacoesAdicionais, original.informacoesAdicionais);
  assert.equal(original.indicadorPresenca, "1");
  assert.equal("intermediador" in original, false);
});

test("operação direta remove intermediador e leitura preserva outras operações existentes", () => {
  const original = {
    indicadorPresenca: "2",
    intermediador: { cnpj: "11222333000181", identificadorCadastro: "LOJA-ANTERIOR" },
  };
  assert.equal(canalComercialClone(original), "intermediacao_existente");
  const copia = atualizarCanalClone(original, "venda_direta_online");
  assert.equal(copia.indicadorPresenca, "2");
  assert.equal("intermediador" in copia, false);
  assert.equal(original.intermediador.identificadorCadastro, "LOJA-ANTERIOR");
  assert.equal(canalComercialClone({ indicadorPresenca: "9" }), "preservar");
});
