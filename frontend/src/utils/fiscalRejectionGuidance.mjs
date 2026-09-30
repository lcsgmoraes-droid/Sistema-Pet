export const SUPORTE_FISCAL_COREPET_URL =
  "https://wa.me/5518997401641?text=" +
  encodeURIComponent("Olá! Preciso de ajuda com uma nota fiscal rejeitada (código 974).");

export const MENSAGEM_SUPORTE_RESPONSAVEL_TECNICO =
  "Entre em contato com o suporte do CorePet e informe o código 974.";

export function rejeicaoResponsavelTecnico(rejeicao) {
  const codigo = String(rejeicao?.codigo || "").trim();
  const motivo = String(rejeicao?.motivo || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  return codigo === "974" || /cnpj do responsavel tecnico/.test(motivo);
}
