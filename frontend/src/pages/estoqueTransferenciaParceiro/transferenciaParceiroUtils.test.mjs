import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularDiferencaLancadaTransferencia,
  calcularTotalDiferencaLancadaTransferencia,
  COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  COLUNAS_DOCUMENTO_TRANSFERENCIA_RETIRADA,
  criarFiltrosHistoricoTransferencia,
  criarFormBaixaTransferencia,
  criarFormTransferencia,
  criarHistoricoTransferenciasVazio,
  criarItemTransferencia,
  criarItensEdicaoTransferencia,
  distribuirBaixaTransferencias,
  documentoTransferenciaTemValores,
  distribuirCompensacaoAutomatica,
  extrairListaProdutos,
  extrairObservacaoManualTransferencia,
  formatarData,
  incrementarItemTransferencia,
  montarCompensacoesBaixaPayload,
  montarCupomTransferencia,
  montarBaixaLoteTransferenciaPayload,
  montarFiltrosHistoricoTransferenciaParams,
  montarParametrosDocumentoTransferencia,
  montarPayloadTransferencia,
  normalizarColunasDocumentoTransferencia,
  normalizarNumero,
  produtoConfereCodigo,
} from "./transferenciaParceiroUtils.js";

test("normalizarColunasDocumentoTransferencia aceita array e string preservando ordem valida", () => {
  assert.deepEqual(
    normalizarColunasDocumentoTransferencia(" total, codigo, invalida, quantidade "),
    ["codigo", "quantidade", "total"],
  );
  assert.deepEqual(normalizarColunasDocumentoTransferencia(["produto", "totais", "produto"]), [
    "produto",
    "totais",
  ]);
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
  assert.equal(
    extrairObservacaoManualTransferencia("Entrega combinada\n\nItens:\nProduto"),
    "Entrega combinada",
  );
});

test("factories de estado preservam defaults e overrides da tela", () => {
  assert.equal(criarFormTransferencia({ documento: "TRP-1" }).documento, "TRP-1");
  assert.equal(criarFormBaixaTransferencia().modo_baixa, "recebimento");
  assert.deepEqual(criarFiltrosHistoricoTransferencia({ busca: "lucas" }), {
    busca: "lucas",
    status_filtro: "",
    data_inicio: "",
    data_fim: "",
    parceiro_id: "",
  });
  assert.equal(criarHistoricoTransferenciasVazio().totais.saldo_aberto, 0);
  assert.deepEqual(criarHistoricoTransferenciasVazio({ totais: { recebidas: 2 } }).totais, {
    total_registros: 0,
    valor_total: 0,
    valor_recebido: 0,
    saldo_aberto: 0,
    pendentes: 0,
    recebidas: 2,
    vencidas: 0,
  });
});

test("montarFiltrosHistoricoTransferenciaParams prioriza pessoa selecionada por id", () => {
  assert.deepEqual(
    montarFiltrosHistoricoTransferenciaParams({
      busca: "Maiara",
      parceiro_id: "8406",
      status_filtro: "pendente",
      data_inicio: "2026-06-01",
      data_fim: "2026-06-30",
    }),
    {
      parceiro_id: "8406",
      status_filtro: "pendente",
      data_inicio: "2026-06-01",
      data_fim: "2026-06-30",
    },
  );

  assert.deepEqual(
    montarFiltrosHistoricoTransferenciaParams({
      busca: "TRP-2026",
      parceiro_id: "",
    }),
    { busca: "TRP-2026" },
  );
});

test("helpers de item e payload mantem calculos da transferencia", () => {
  const produto = {
    id: 10,
    nome: "Defenza",
    codigo: "DEF",
    codigo_barras: "789",
    estoque_atual: 3,
    preco_custo: 20.5,
  };
  const item = criarItemTransferencia(produto, 123);
  assert.deepEqual(item, {
    uid: "10-123",
    produto_id: 10,
    produto_nome: "Defenza",
    codigo: "DEF",
    codigo_barras: "789",
    estoque_atual: 3,
    custo_base_unitario: 20.5,
    custo_unitario: 20.5,
    quantidade: 1,
    total_item: 20.5,
  });
  assert.deepEqual(incrementarItemTransferencia(item, { estoque_atual: 2 }), {
    ...item,
    quantidade: 2,
    total_item: 41,
    estoque_atual: 2,
  });
  assert.deepEqual(
    montarPayloadTransferencia(
      7,
      { data_vencimento: "2026-05-31", documento: " TRP ", observacao: " obs " },
      [item],
    ),
    {
      parceiro_id: 7,
      data_vencimento: "2026-05-31",
      documento: "TRP",
      observacao: "obs",
      itens: [
        {
          produto_id: 10,
          quantidade: 1,
          custo_unitario: 20.5,
          valor_total: 20.5,
        },
      ],
    },
  );
});

test("helpers calculam diferenca do valor lancado contra o custo base", () => {
  assert.equal(
    calcularDiferencaLancadaTransferencia({
      quantidade: 2,
      custo_base_unitario: 20,
      custo_unitario: 25,
      total_item: 50,
    }),
    10,
  );
  assert.equal(
    calcularDiferencaLancadaTransferencia({
      quantidade: 1,
      custo_base_unitario: 20,
      custo_unitario: 18,
      total_item: 18,
    }),
    -2,
  );
  assert.equal(
    calcularTotalDiferencaLancadaTransferencia([
      { quantidade: 2, custo_base_unitario: 20, total_item: 50 },
      { quantidade: 1, custo_base_unitario: 20, total_item: 18 },
    ]),
    8,
  );
});

test("helpers de edicao e baixa normalizam itens e compensacoes", () => {
  assert.deepEqual(
    criarItensEdicaoTransferencia(
      {
        conta_receber_id: 5,
        itens: [
          {
            produto_id: 10,
            produto_nome: "Defenza",
            codigo: "DEF",
            codigo_barras: "789",
            estoque_atual: 3,
            custo_unitario: "20",
            quantidade: "2",
            valor_total: "40",
          },
        ],
      },
      999,
    ),
    [
      {
        uid: "edit-5-10-0-999",
        produto_id: 10,
        produto_nome: "Defenza",
        codigo: "DEF",
        codigo_barras: "789",
        estoque_atual: 3,
        custo_base_unitario: 20,
        custo_unitario: 20,
        quantidade: 2,
        total_item: 40,
      },
    ],
  );
  assert.deepEqual(montarCompensacoesBaixaPayload({ 1: "10,50", 2: "", x: "2" }), [
    { conta_pagar_id: 1, valor_compensado: 10.5 },
  ]);
  assert.deepEqual(
    distribuirCompensacaoAutomatica("35", [
      { conta_pagar_id: 1, saldo_aberto: 20 },
      { conta_pagar_id: 2, saldo_aberto: 30 },
    ]),
    { 1: "20.00", 2: "15.00" },
  );
});

test("distribuirBaixaTransferencias preenche valores da mais antiga para a mais nova", () => {
  const registros = [
    { conta_receber_id: 1, data_emissao: "2026-06-01", saldo_aberto: 400 },
    { conta_receber_id: 2, data_emissao: "2026-06-02", saldo_aberto: 400 },
    { conta_receber_id: 3, data_emissao: "2026-06-03", saldo_aberto: 400 },
  ];

  assert.deepEqual(distribuirBaixaTransferencias("1000", registros, "antiga"), {
    1: "400.00",
    2: "400.00",
    3: "200.00",
  });
});

test("distribuirBaixaTransferencias pode priorizar a transferencia mais nova", () => {
  const registros = [
    { conta_receber_id: 1, data_emissao: "2026-06-01", saldo_aberto: 400 },
    { conta_receber_id: 2, data_emissao: "2026-06-02", saldo_aberto: 400 },
    { conta_receber_id: 3, data_emissao: "2026-06-03", saldo_aberto: 400 },
  ];

  assert.deepEqual(distribuirBaixaTransferencias("700", registros, "nova"), {
    3: "400.00",
    2: "300.00",
  });
});

test("montarBaixaLoteTransferenciaPayload envia apenas aplicacoes marcadas com valor", () => {
  assert.deepEqual(
    montarBaixaLoteTransferenciaPayload({
      parceiroId: 7,
      form: {
        modo_baixa: "recebimento",
        data_recebimento: "2026-07-01",
        forma_pagamento_id: "3",
        observacao: "Pix recebido",
        devolver_estoque: false,
      },
      aplicacoes: { 10: "100", 11: "", 12: "0", 13: "25,50" },
      compensacoes: {},
    }),
    {
      parceiro_id: 7,
      modo_baixa: "recebimento",
      data_recebimento: "2026-07-01",
      forma_pagamento_id: 3,
      observacao: "Pix recebido",
      devolver_estoque: false,
      aplicacoes: [
        { conta_receber_id: 10, valor_baixado: 100 },
        { conta_receber_id: 13, valor_baixado: 25.5 },
      ],
      compensacoes: [],
    },
  );
});

test("montarBaixaLoteTransferenciaPayload inclui nova conta a pagar no acerto", () => {
  assert.deepEqual(
    montarBaixaLoteTransferenciaPayload({
      parceiroId: 7,
      form: {
        modo_baixa: "acerto",
        data_recebimento: "2026-07-01",
        observacao: "Mata mensal",
        devolver_estoque: false,
        nova_conta_pagar_acerto: {
          descricao: "Compra mercadoria parceira",
          valor: "250,50",
          data_vencimento: "2026-07-10",
          documento: "ACERTO-1",
          observacao: "Produtos pegos no parceiro",
        },
      },
      aplicacoes: { 10: "250,50" },
      compensacoes: {},
    }),
    {
      parceiro_id: 7,
      modo_baixa: "acerto",
      data_recebimento: "2026-07-01",
      observacao: "Mata mensal",
      devolver_estoque: false,
      aplicacoes: [{ conta_receber_id: 10, valor_baixado: 250.5 }],
      compensacoes: [],
      nova_conta_pagar_acerto: {
        descricao: "Compra mercadoria parceira",
        valor: 250.5,
        data_vencimento: "2026-07-10",
        documento: "ACERTO-1",
        observacao: "Produtos pegos no parceiro",
      },
    },
  );
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
