export function obterContextoRevisaoCaixa() {
  if (typeof window === "undefined" || !window.location.pathname.endsWith("/pdv")) return null;
  const params = new URLSearchParams(window.location.search);
  const emRevisao = ["caixa_revisao_id", "data_ocorrencia", "motivo_revisao"]
    .some((campo) => params.has(campo));
  if (!emRevisao) return null;
  const caixaId = Number(params.get("caixa_revisao_id"));
  const dataOcorrencia = params.get("data_ocorrencia");
  const motivo = params.get("motivo_revisao")?.trim();
  if (!Number.isInteger(caixaId) || caixaId <= 0 || !dataOcorrencia || !motivo) {
    throw new Error("Revisão incompleta. Volte à tela de caixas e inicie novamente.");
  }
  return {
    caixa_revisao_id: caixaId,
    data_ocorrencia: dataOcorrencia,
    motivo_revisao: motivo,
  };
}
