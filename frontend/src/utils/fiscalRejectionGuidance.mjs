export const RECEITA_PR_PORTAL_URL = "https://receita.pr.gov.br/login";

export function rejeicaoResponsavelTecnico(rejeicao) {
  const codigo = String(rejeicao?.codigo || "").trim();
  const motivo = String(rejeicao?.motivo || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  return codigo === "974" || /cnpj do responsavel tecnico/.test(motivo);
}
