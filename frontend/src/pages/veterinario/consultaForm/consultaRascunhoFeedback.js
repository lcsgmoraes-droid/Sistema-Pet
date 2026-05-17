import { ETAPAS } from "./consultaFormUtils.js";

export const RASCUNHO_SALVO_ACOES = Object.freeze({
  CONTINUAR: "continuar",
  TOPO: "topo",
  LISTA: "lista",
});

export function buildMensagemRascunhoSalvo({
  etapa,
  totalEtapas = ETAPAS.length,
} = {}) {
  return etapa < totalEtapas - 1
    ? "Rascunho salvo com sucesso."
    : "Rascunho salvo com sucesso. Voce pode finalizar quando quiser.";
}

export function listarAcoesRascunhoSalvo() {
  return [
    {
      id: RASCUNHO_SALVO_ACOES.CONTINUAR,
      label: "Continuar editando",
    },
    {
      id: RASCUNHO_SALVO_ACOES.TOPO,
      label: "Ir para o topo",
    },
    {
      id: RASCUNHO_SALVO_ACOES.LISTA,
      label: "Sair para lista",
    },
  ];
}
