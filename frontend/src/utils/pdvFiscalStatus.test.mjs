import assert from "node:assert/strict";
import test from "node:test";

import {
  extrairCamposFiscaisVenda,
  obterSituacaoFiscalVenda,
  podeImprimirDocumentoFiscalVenda,
  rotaDanfeFiscalVenda,
  rotaNotaFiscalVenda,
  temDocumentoFiscalVenda,
} from "./pdvFiscalStatus.js";

test("não exibe situação fiscal quando a venda nunca teve nota", () => {
  assert.equal(temDocumentoFiscalVenda({ id: 10, status: "finalizada" }), false);
  assert.equal(obterSituacaoFiscalVenda({ id: 10 }), null);
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
