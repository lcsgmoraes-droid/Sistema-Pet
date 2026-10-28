import assert from "node:assert/strict";
import test from "node:test";

import {
  extrairCamposFiscaisVenda,
  obterSituacaoFiscalVenda,
  obterPendenciaCancelamentoFiscal,
  podeCancelarVenda,
  podeImprimirDocumentoFiscalVenda,
  rotaDanfeFiscalVenda,
  rotaNotaFiscalVenda,
  temDocumentoFiscalVenda,
  temNotaFiscalAtiva,
} from "./pdvFiscalStatus.js";

test("não exibe situação fiscal quando a venda nunca teve nota", () => {
  assert.equal(temDocumentoFiscalVenda({ id: 10, status: "finalizada" }), false);
  assert.equal(obterSituacaoFiscalVenda({ id: 10 }), null);
});

test("pendência salva com HTML 502 exibe orientação sem o corpo da página de erro", () => {
  const pendencia = obterPendenciaCancelamentoFiscal({
    id: 26,
    status: "finalizada",
    nfe_status: "autorizada",
    nfe_cancelamento_status: "pendente",
    nfe_cancelamento_motivo: "<html><body><h1>502 Bad Gateway</h1>nginx</body></html>",
  });
  assert.match(pendencia.detalhe, /temporariamente indisponível/);
  assert.doesNotMatch(pendencia.detalhe, /html|nginx|Bad Gateway/);
});

test("resume uma NF-e rejeitada com código e motivo", () => {
  const situacao = obterSituacaoFiscalVenda({
    nfe_tipo: "nfe",
    nfe_modelo: "55",
    nfe_numero: 1630,
    nfe_status: "rejeitada",
    nfe_codigo_erro: "963",
    nfe_motivo_rejeicao: "Tipo de pagamento não aceita o grupo de cartões ou boletos",
  });

  assert.equal(situacao.label, "NF-e 1630: Rejeitada");
  assert.equal(situacao.intent, "danger");
  assert.match(situacao.detalhe, /Código 963/);
  assert.match(situacao.detalhe, /Tipo de pagamento/);
});

test("resume rejeição técnica como atendimento do suporte, sem instrução fiscal ao cliente", () => {
  const situacao = obterSituacaoFiscalVenda({
    nfe_tipo: "nfe",
    nfe_status: "rejeitada",
    nfe_codigo_erro: "974",
    nfe_motivo_rejeicao: "CNPJ do responsável técnico diverge do cadastrado",
  });

  assert.match(situacao.detalhe, /suporte do CorePet/);
  assert.doesNotMatch(situacao.detalhe, /CNPJ do responsável técnico/);
});

test("distingue NFC-e autorizada e cancelada", () => {
  assert.equal(
    obterSituacaoFiscalVenda({ nfe_modelo: 65, nfe_numero: 530, nfe_status: "autorizada" }).label,
    "NFC-e 530: Autorizada",
  );
  assert.equal(
    obterSituacaoFiscalVenda({ nfe_tipo: "nfce", nfe_status: "cancelada" }).intent,
    "danger",
  );
});

test("cancelamento comercial é permitido independentemente da situação fiscal da nota", () => {
  const venda = { id: 26, status: "pago_nf", nfe_modelo: 65 };
  assert.equal(podeCancelarVenda({ ...venda, nfe_status: "cancelada" }), true);
  assert.equal(podeCancelarVenda({ ...venda, nfe_status: "Cancelada" }), true);
  for (const nfe_status of ["autorizada", "processando", "inconclusiva", "rejeitada", null]) {
    assert.equal(podeCancelarVenda({ ...venda, nfe_status }), true);
  }
});

test("venda cancelada mantém nota autorizada e mostra código e motivo da recusa", () => {
  const venda = {
    id: 26,
    status: "cancelada",
    nfe_status: "autorizada",
    nfe_cancelamento_status: "recusado",
    nfe_cancelamento_codigo: "501",
    nfe_cancelamento_motivo: { mensagem: "Prazo de cancelamento excedido" },
  };
  assert.equal(obterSituacaoFiscalVenda(venda).statusLabel, "Autorizada");
  const pendencia = obterPendenciaCancelamentoFiscal(venda);
  assert.equal(pendencia.label, "Nota a cancelar");
  assert.match(pendencia.detalhe, /Código 501/);
  assert.match(pendencia.detalhe, /Prazo de cancelamento excedido/);
  assert.doesNotMatch(pendencia.detalhe, /object Object/);
});

test("pedido fiscal em andamento só deixa de ser pendência após confirmação da nota cancelada", () => {
  const venda = {
    id: 26,
    status: "cancelada",
    nfe_status: "autorizada",
    nfe_cancelamento_status: "solicitado",
  };
  assert.equal(obterPendenciaCancelamentoFiscal(venda).label, "Cancelamento da nota em andamento");
  assert.equal(
    obterPendenciaCancelamentoFiscal({
      ...venda,
      nfe_status: "cancelada",
      nfe_cancelamento_status: "confirmado",
    }),
    null,
  );
  assert.equal(
    obterPendenciaCancelamentoFiscal({
      id: 27,
      status: "cancelada",
      pendencia_fiscal_cancelamento: false,
    }),
    null,
  );
  assert.equal(temDocumentoFiscalVenda({ id: 27, pendencia_fiscal_cancelamento: false }), false);
});

test("rejeição após autorização preserva a pendência fiscal informada pelo servidor", () => {
  const venda = {
    id: 26,
    status: "cancelada",
    nfe_status: "rejeitada",
    nfe_data_autorizacao: "2026-10-20T12:00:00",
    pendencia_fiscal_cancelamento: true,
  };
  assert.equal(temNotaFiscalAtiva(venda), true);
  assert.equal(obterPendenciaCancelamentoFiscal(venda).label, "Nota a cancelar");
  assert.equal(obterSituacaoFiscalVenda(venda).statusLabel, "Rejeitada");
});

test("rascunho sem autorização anterior não cria pendência para a venda cancelada", () => {
  const venda = {
    id: 26,
    status: "cancelada",
    nfe_status: "rascunho",
    nfe_correlation_id: "rascunho-26",
  };
  assert.equal(temNotaFiscalAtiva(venda), false);
  assert.equal(obterPendenciaCancelamentoFiscal(venda), null);
});

test("nota cancelada confirmada prevalece sobre sinal antigo de pendência", () => {
  for (const nfe_status of ["cancelada", "cancelado"]) {
    const venda = { id: 26, status: "cancelada", nfe_status, pendencia_fiscal_cancelamento: true };
    assert.equal(temNotaFiscalAtiva(venda), false);
    assert.equal(obterPendenciaCancelamentoFiscal(venda), null);
  }
});

test("nota cancelada não libera novo cancelamento em venda cancelada ou devolvida", () => {
  const venda = { id: 26, nfe_status: "cancelada" };
  for (const status of [
    "cancelada",
    "cancelado",
    "finalizada_devolucao",
    "finalizada_devolucao_parcial",
    "devolvida_total",
    "finalizada_devolucao_total",
  ]) {
    assert.equal(podeCancelarVenda({ ...venda, status }), false);
  }
  assert.equal(podeCancelarVenda({ nfe_status: "cancelada", status: "aberta" }), false);
  for (const status of ["aberta", "finalizada", "baixa_parcial"]) {
    assert.equal(podeCancelarVenda({ ...venda, status }), true);
  }
});

test("preserva todos os campos fiscais ao abrir a venda no PDV", () => {
  const campos = extrairCamposFiscaisVenda({
    nfe_status: "rejeitada",
    nfe_numero: 1630,
    nfe_chave: "123",
    outro_campo: "ignorado",
  });

  assert.equal(campos.nfe_status, "rejeitada");
  assert.equal(campos.nfe_numero, 1630);
  assert.equal(campos.nfe_chave, "123");
  assert.equal(campos.nfe_tipo, null);
  assert.equal("outro_campo" in campos, false);
});

test("monta acesso direto da venda para a nota fiscal", () => {
  assert.equal(
    rotaNotaFiscalVenda({ id: 26, nfe_modelo: 55, nfe_numero: 1631 }),
    "/notas-fiscais/saida?abrir=1&busca=1631&venda_id=26",
  );
  assert.equal(rotaNotaFiscalVenda({ id: 26 }), null);
  assert.equal(
    rotaNotaFiscalVenda({ id: 26, nfe_modelo: 65, nfe_numero: 66, nfe_status: "rejeitada" }),
    "/notas-fiscais/saida?abrir=1&busca=66&venda_id=26&corrigir=1",
  );
});

test("monta a rota do DANFE conforme o provedor fiscal", () => {
  assert.equal(
    rotaDanfeFiscalVenda({
      id: 26,
      nfe_modelo: 65,
      nfe_provider: "intnfe",
      nfe_correlation_id: "corr-26",
    }),
    "/nfe/vendas/26/danfe",
  );
  assert.equal(
    rotaDanfeFiscalVenda({
      id: 27,
      nfe_modelo: 55,
      nfe_provider: "bling",
      nfe_bling_id: 910,
    }),
    "/nfe/910/danfe",
  );
});

test("só permite imprimir documento fiscal autorizado", () => {
  const venda = {
    id: 26,
    nfe_modelo: 65,
    nfe_provider: "intnfe",
    nfe_correlation_id: "corr-26",
  };

  assert.equal(podeImprimirDocumentoFiscalVenda({ ...venda, nfe_status: "autorizada" }), true);
  assert.equal(podeImprimirDocumentoFiscalVenda({ ...venda, nfe_status: "processando" }), false);
  assert.equal(podeImprimirDocumentoFiscalVenda({ ...venda, nfe_status: "rejeitada" }), false);
});
