let dialogoAtual = null;
let proximoId = 1;
const fila = [];
const ouvintes = new Set();

function notificar() {
  ouvintes.forEach((ouvinte) => ouvinte(dialogoAtual));
}

function exibirProximo() {
  dialogoAtual = fila.shift() || null;
  notificar();
}

export function assinarCorrecaoFiscal(ouvinte) {
  ouvintes.add(ouvinte);
  ouvinte(dialogoAtual);
  return () => ouvintes.delete(ouvinte);
}

export function solicitarCorrecaoFiscal(configuracao) {
  return new Promise((resolve) => {
    fila.push({ id: proximoId++, ...configuracao, resolve });
    if (!dialogoAtual) exibirProximo();
  });
}

export function resolverCorrecaoFiscal(valor) {
  if (!dialogoAtual) return;
  const { resolve } = dialogoAtual;
  dialogoAtual = null;
  resolve(valor);
  exibirProximo();
}
