import assert from "node:assert/strict";
import test from "node:test";
import { resumirCancelamentoNota } from "./nfeCancelamentoFeedback.js";

test("recusa fiscal 501 exibe código e motivo sem sugerir cancelamento confirmado", () => {
  const feedback = resumirCancelamentoNota({
    success: false,
    cancelamento_status: "recusado",
    cancelamento_codigo: "501",
    cancelamento_motivo: { mensagem: "Prazo de cancelamento excedido" },
    cancelamento_solicitado: false,
    situacao: "autorizada",
  });
  assert.equal(feedback.confirmado, false);
  assert.equal(feedback.solicitado, false);
  assert.match(feedback.mensagem, /recusado/);
  assert.match(feedback.mensagem, /Código 501/);
  assert.match(feedback.mensagem, /Prazo de cancelamento excedido/);
  assert.doesNotMatch(feedback.mensagem, /com sucesso|object Object/);
});

test("resposta HTTP estruturada de recusa também é legível", () => {
  const feedback = resumirCancelamentoNota({
    detail: {
      cancelamento_status: "recusado",
      codigo: 501,
      motivo: { detail: { message: "Cancelamento fora do prazo" } },
    },
  });
  assert.match(feedback.mensagem, /Código 501/);
  assert.match(feedback.mensagem, /fora do prazo/);
  assert.doesNotMatch(feedback.mensagem, /object Object/);
});

test("pedido aceito continua em andamento até confirmação do cancelamento", () => {
  const pendente = resumirCancelamentoNota({
    cancelamento_status: "solicitado",
    cancelamento_solicitado: true,
    situacao: "autorizada",
  });
  assert.equal(pendente.confirmado, false);
  assert.equal(pendente.solicitado, true);
  assert.match(pendente.mensagem, /em andamento/);
  const confirmado = resumirCancelamentoNota({
    cancelamento_status: "confirmado",
    success: true,
    situacao: "cancelada",
  });
  assert.equal(confirmado.confirmado, true);
  assert.equal(confirmado.solicitado, false);
  assert.match(confirmado.mensagem, /com confirmação do emissor/);
});

test("resposta vazia ou sucesso genérico nunca inventa cancelamento fiscal", () => {
  for (const payload of [null, {}, { success: true }, { processando: true }]) {
    const feedback = resumirCancelamentoNota(payload);
    assert.equal(feedback.confirmado, false);
    assert.equal(feedback.solicitado, false);
    assert.match(feedback.mensagem, /não foi confirmado/);
  }
});

test("falha 502 em HTML vira orientação sem confirmar cancelamento", () => {
  const html = "<html><head><title>502 Bad Gateway</title></head><body>nginx</body></html>";
  for (const payload of [html, { detail: html }, { cancelamento_motivo: { mensagem: html } }]) {
    const feedback = resumirCancelamentoNota(payload);
    assert.equal(feedback.confirmado, false);
    assert.equal(feedback.solicitado, false);
    assert.match(feedback.mensagem, /temporariamente indisponível/);
    assert.match(feedback.mensagem, /Consulte a situação da nota/);
    assert.doesNotMatch(feedback.mensagem, /<html|nginx|Bad Gateway/);
  }
});

test("falha de rede não expõe exceção técnica nem confirma cancelamento", () => {
  const feedback = resumirCancelamentoNota({ mensagem: "Network Error" });
  assert.equal(feedback.confirmado, false);
  assert.match(feedback.motivo, /temporariamente indisponível/);
  assert.doesNotMatch(feedback.mensagem, /Network Error/);
});
