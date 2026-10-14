import assert from "node:assert/strict";
import { test } from "node:test";
import { criarConsultaCaixaAberto } from "./caixaAbertoRequest.js";

function pendente() {
  let resolve;
  let reject;
  const promise = new Promise((sucesso, falha) => {
    resolve = sucesso;
    reject = falha;
  });
  return { promise, resolve, reject };
}

test("deduplica consultas simultâneas do mesmo formato", async () => {
  const resposta = pendente();
  let chamadas = 0;
  const consultar = criarConsultaCaixaAberto(() => {
    chamadas += 1;
    return resposta.promise;
  });
  const primeira = consultar();
  const segunda = consultar();
  assert.equal(primeira, segunda);
  await Promise.resolve();
  assert.equal(chamadas, 1);
  resposta.resolve({ id: 1, movimentacoes: [{ id: 2 }] });
  assert.deepEqual(await primeira, { id: 1, movimentacoes: [{ id: 2 }] });
});

test("compacto e completo não compartilham resposta nem removem movimentações de outros consumidores", async () => {
  const completo = pendente();
  const compacto = pendente();
  const consultar = criarConsultaCaixaAberto(({ compact }) =>
    compact ? compacto.promise : completo.promise,
  );
  const respostaCompleta = consultar();
  const respostaCompacta = consultar({ compact: true });
  assert.notEqual(respostaCompleta, respostaCompacta);
  compacto.resolve({ id: 1 });
  assert.deepEqual(await respostaCompacta, { id: 1 });
  completo.resolve({ id: 1, movimentacoes: [{ id: 2 }] });
  assert.deepEqual(await respostaCompleta, { id: 1, movimentacoes: [{ id: 2 }] });
});

test("consulta concluída não mantém cache quando o caixa muda", async () => {
  let chamadas = 0;
  const consultar = criarConsultaCaixaAberto(async () => ({ id: ++chamadas }));
  assert.equal((await consultar()).id, 1);
  assert.equal((await consultar()).id, 2);
});

test("falha libera nova tentativa sem compartilhar a rejeição anterior", async () => {
  let chamadas = 0;
  const consultar = criarConsultaCaixaAberto(async () => {
    chamadas += 1;
    if (chamadas === 1) throw new Error("timeout");
    return null;
  });
  const primeira = consultar({ compact: true });
  const repetida = consultar({ compact: true });
  assert.equal(primeira, repetida);
  await assert.rejects(primeira, /timeout/);
  assert.equal(await consultar({ compact: true }), null);
  assert.equal(chamadas, 2);
});

test("cancelamento de uma tela não aborta consultas de outras telas", async () => {
  const compartilhada = pendente();
  const consultar = criarConsultaCaixaAberto(({ signal }) => {
    if (!signal) return compartilhada.promise;
    return new Promise((resolve, reject) => {
      signal.addEventListener("abort", () => reject(new Error("cancelado")), { once: true });
    });
  });
  const controller = new AbortController();
  const outraTela = consultar({ compact: true });
  const cancelavel = consultar({ compact: true, signal: controller.signal });
  const falhou = assert.rejects(cancelavel, /cancelado/);
  controller.abort();
  await falhou;
  compartilhada.resolve({ id: 7 });
  assert.deepEqual(await outraTela, { id: 7 });
});
