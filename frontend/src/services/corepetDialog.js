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

function solicitarDialogo(configuracao) {
  return new Promise((resolve) => {
    fila.push({
      id: proximoId++,
      ...configuracao,
      resolve,
    });

    if (!dialogoAtual) {
      exibirProximo();
    }
  });
}

export function assinarCorePetDialog(ouvinte) {
  ouvintes.add(ouvinte);
  ouvinte(dialogoAtual);
  return () => ouvintes.delete(ouvinte);
}

export function resolverCorePetDialog(valor) {
  if (!dialogoAtual) return;

  const { resolve } = dialogoAtual;
  dialogoAtual = null;
  resolve(valor);
  exibirProximo();
}

export function confirmarCorePet(opcoes) {
  const configuracao = typeof opcoes === "string" ? { mensagem: opcoes } : opcoes;
  const texto = String(configuracao?.mensagem || "").toLocaleLowerCase("pt-BR");
  const acaoPerigosa = /(exclu|cancel|remov|desativ|inativ|estorn|desvinc|anul|descart)/.test(texto);

  return solicitarDialogo({
    tipo: "confirmacao",
    titulo: acaoPerigosa ? "Atenção" : "Confirmar ação",
    confirmarTexto: "Confirmar",
    cancelarTexto: "Cancelar",
    variante: acaoPerigosa ? "danger" : "question",
    ...configuracao,
  });
}

export function perguntarCorePet(opcoes, valorInicial = "") {
  const configuracao =
    typeof opcoes === "string" ? { mensagem: opcoes, valorInicial } : opcoes;

  return solicitarDialogo({
    tipo: "entrada",
    titulo: "Preencha os dados",
    confirmarTexto: "Continuar",
    cancelarTexto: "Cancelar",
    variante: "info",
    valorInicial: "",
    ...configuracao,
  });
}
