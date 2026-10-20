import assert from "node:assert/strict";
import test from "node:test";
import {
  documentosEstornoDisponiveis,
  notaPermiteAcompanharEstorno,
  obterSituacaoEstorno,
  podeEmitirEstorno,
} from "./nfeEstorno.js";
import { obterPendenciaCancelamentoFiscal, obterSituacaoFiscalVenda } from "./pdvFiscalStatus.js";

const previa = {
  modelo: 55,
  tipo_operacao: "entrada",
  finalidade: "ajuste",
  original: { chave: "1".repeat(44) },
};
const dados = { elegivel: true, bloqueios: [], previa, estorno: null };
const confirmado = { declarado: true, motivo: "Operação não realizada e mercadoria não saiu." };

test("só permite primeira emissão com prévia válida, motivo e declaração expressa", () => {
  assert.equal(podeEmitirEstorno(dados, confirmado), true);
  assert.equal(podeEmitirEstorno(dados, { ...confirmado, declarado: false }), false);
  assert.equal(podeEmitirEstorno(dados, { ...confirmado, motivo: "curto" }), false);
  assert.equal(podeEmitirEstorno({ ...dados, elegivel: false }, confirmado), false);
  assert.equal(
    podeEmitirEstorno({ ...dados, bloqueios: ["Destinatário não identificado"] }, confirmado),
    false,
  );
  assert.equal(
    podeEmitirEstorno(
      { ...dados, previa: { ...previa, original: { chave: "inválida" } } },
      confirmado,
    ),
    false,
  );
  assert.equal(podeEmitirEstorno(dados, { ...confirmado, envioIniciado: true }), false);
});

test("uma tentativa persistida impede novo envio inclusive após rejeição ou resultado incerto", () => {
  for (const status of [
    "enviando",
    "incerto",
    "processando",
    "autorizado",
    "rejeitado",
    "denegado",
    "cancelado",
    "divergente",
  ]) {
    assert.equal(podeEmitirEstorno({ ...dados, estorno: { id: 7, status } }, confirmado), false);
  }
});

test("XML e DANFE exigem autorização do estorno, XML validado e protocolo próprio", () => {
  const estorno = { status: "autorizado", protocolo: "1".repeat(15), xml_validado: true };
  assert.equal(documentosEstornoDisponiveis({ estorno }), true);
  assert.equal(
    documentosEstornoDisponiveis({ estorno: { ...estorno, xml_validado: false } }),
    false,
  );
  assert.equal(documentosEstornoDisponiveis({ estorno: { ...estorno, protocolo: null } }), false);
  assert.equal(
    documentosEstornoDisponiveis({ estorno: { ...estorno, status: "processando" } }),
    false,
  );
});

test("regularização por estorno fecha pendência sem cancelar NFC-e original", () => {
  const venda = {
    id: 2,
    status: "cancelada",
    nfe_status: "autorizada",
    nfe_modelo: 65,
    nfe_estorno_status: "autorizado",
    nfe_estorno_numero: 99,
    nfe_estorno_protocolo: "1".repeat(15),
    pendencia_fiscal_cancelamento: false,
  };
  assert.equal(obterSituacaoFiscalVenda(venda).statusLabel, "Autorizada");
  assert.equal(obterSituacaoEstorno(venda).label, "NF-e de estorno autorizada");
  assert.equal(obterPendenciaCancelamentoFiscal(venda), null);
});

test("rejeição 974 preserva motivo, pendência e situação fiscal da nota original", () => {
  const venda = {
    status: "cancelada",
    nfe_status: "autorizada",
    pendencia_fiscal_cancelamento: true,
    estorno: {
      id: 7,
      status: "rejeitado",
      codigo: "974",
      motivo: "CNPJ do responsavel tecnico diverge do cadastrado",
      xml_validado: false,
    },
  };
  const situacao = obterSituacaoEstorno(venda);
  assert.equal(situacao.label, "NF-e de estorno rejeitada");
  assert.equal(situacao.estorno.codigo, "974");
  assert.equal(situacao.detalhe, "CNPJ do responsavel tecnico diverge do cadastrado");
  assert.equal(obterSituacaoFiscalVenda(venda).statusLabel, "Autorizada");
  assert.ok(obterPendenciaCancelamentoFiscal(venda));
  assert.equal(documentosEstornoDisponiveis(venda), false);
  assert.equal(podeEmitirEstorno({ ...dados, estorno: venda.estorno }, confirmado), false);
});

test("ação de estorno é vinculada à venda cancelada e permanece para consultar documento existente", () => {
  const nota = {
    provedor: "intnfe",
    venda_id: 2,
    venda_status: "cancelada",
    modelo: 65,
    status: "autorizada",
    pendencia_fiscal_cancelamento: true,
  };
  assert.equal(notaPermiteAcompanharEstorno(nota), true);
  assert.equal(notaPermiteAcompanharEstorno({ ...nota, venda_status: "finalizada" }), false);
  assert.equal(notaPermiteAcompanharEstorno({ ...nota, modelo: 55 }), false);
  assert.equal(notaPermiteAcompanharEstorno({ ...nota, provedor: "bling" }), false);
  assert.equal(
    notaPermiteAcompanharEstorno({
      ...nota,
      nfe_estorno_status: "autorizado",
      pendencia_fiscal_cancelamento: false,
    }),
    true,
  );
});
