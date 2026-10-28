let dialogoAtual = null;
let proximoId = 1;
const fila = [];
const ouvintes = new Set();

function notificar() {
  ouvintes.forEach((ouvinte) => ouvinte(dialogoAtual));
}

export function assinarDadosAdicionaisNota(ouvinte) {
  ouvintes.add(ouvinte);
  ouvinte(dialogoAtual);
  return () => ouvintes.delete(ouvinte);
}

export function solicitarDadosAdicionaisNota({ vendaId }) {
  return new Promise((resolve) => {
    fila.push({ id: proximoId++, vendaId, resolve });
    if (!dialogoAtual) {
      dialogoAtual = fila.shift();
      notificar();
    }
  });
}

export function resolverDadosAdicionaisNota(id, resultado) {
  if (dialogoAtual?.id !== id) return;
  const { resolve } = dialogoAtual;
  dialogoAtual = fila.shift() || null;
  resolve(resultado);
  notificar();
}
