import assert from "node:assert/strict";
import { test } from "node:test";

import {
  COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  COLUNAS_DOCUMENTO_TRANSFERENCIA_RETIRADA,
  documentoTransferenciaTemValores,
  extrairListaProdutos,
  extrairObservacaoManualTransferencia,
  formatarData,
  montarCupomTransferencia,
  montarParametrosDocumentoTransferencia,
  normalizarColunasDocumentoTransferencia,
  normalizarNumero,
  produtoConfereCodigo,
} from "./transferenciaParceiroUtils.js";

test("normalizarColunasDocumentoTransferencia aceita array e string preservando ordem valida", () => {
  assert.deepEqual(
    normalizarColunasDocumentoTransferencia(" total, codigo, invalida, quantidade "),
    ["codigo", "quantidade", "total"],
  );
  assert.deepEqual(
    normalizarColunasDocumentoTransferencia(["produto", "totais", "produto"]),
    ["produto", "totais"],
  );
  assert.deepEqual(
    normalizarColunasDocumentoTransferencia(COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO),
    COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  );
});

test("documentoTransferenciaTemValores identifica documentos sem e com custos", () => {
  assert.equal(documentoTransferenciaTemValores(COLUNAS_DOCUMENTO_TRANSFERENCIA_RETIRADA), false);
  assert.equal(documentoTransferenciaTemValores(["codigo", "custo_unitario"]), true);
});

test("montarParametrosDocumentoTransferencia cria flags esperadas para PDF e Excel", () => {
  assert.deepEqual(montarParametrosDocumentoTransferencia(["codigo", "produto", "totais"]), {
    mostrar_codigo: true,
    mostrar_descricao: true,
    mostrar_quantidade: false,
    mostrar_custo_unitario: false,
    mostrar_total_item: false,
    mostrar_totais: true,
  });
});

test("produtoConfereCodigo compara codigo textual e codigo de barras por digitos", () => {
  const produto = {
    codigo: "DEF-123",
    codigo_barras: "789.000.111",
    gtin_ean: "000789",
  };

  assert.equal(produtoConfereCodigo(produto, "def-123"), true);
  assert.equal(produtoConfereCodigo(produto, "789000111"), true);
  assert.equal(produtoConfereCodigo(produto, "999"), false);
});

test("helpers de carga e texto preservam formatos usados na tela", () => {
  assert.deepEqual(extrairListaProdutos({ items: [1, 2] }), [1, 2]);
  assert.deepEqual(extrairListaProdutos({ data: ["a"] }), ["a"]);
  assert.equal(normalizarNumero("12,5"), 12.5);
  assert.equal(formatarData("2026-05-20"), "20/05/2026");
  assert.equal(extrairObservacaoManualTransferencia("Entrega combinada\n\nItens:\nProduto"), "Entrega combinada");
});

test("montarCupomTransferencia respeita colunas de retirada sem valores financeiros", () => {
  const cupom = montarCupomTransferencia(
    {
      documento: "TRP-10",
      parceiro_nome: "Parceiro Teste",
      data_emissao: "2026-05-20",
      data_vencimento: "2026-05-31",
      status_label: "Pendente",
      itens: [
        {
          codigo: "DEF-123",
          produto_nome: "Defenza Antipulgas",
          quantidade: 2,
          custo_unitario: 30,
          valor_total: 60,
        },
      ],
      valor_original: 60,
      valor_recebido: 0,
      saldo_aberto: 60,
    },
    COLUNAS_DOCUMENTO_TRANSFERENCIA_RETIRADA,
  );

  assert.match(cupom, /Documento: TRP-10/);
  assert.match(cupom, /Defenza Antipulgas/);
  assert.match(cupom, /Qtd 2/);
  assert.doesNotMatch(cupom, /Custo un\./);
  assert.doesNotMatch(cupom, /R\$/);
});
