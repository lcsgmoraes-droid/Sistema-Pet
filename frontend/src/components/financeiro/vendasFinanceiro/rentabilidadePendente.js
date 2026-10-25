export const PENDENCIA_IFOOD_LABEL = "Pendente iFood";

export function temRentabilidadePendente(dados = {}) {
  return Boolean(
    dados?.taxas_ifood_pendentes ||
    dados?.rentabilidade_status === "pending_ifood_financial" ||
    Number(dados?.vendas_rentabilidade_pendente || 0) > 0,
  );
}

export function descreverRentabilidadePendente(dados = {}) {
  const quantidade = Number(dados?.vendas_rentabilidade_pendente || 0);
  return quantidade > 0
    ? `${quantidade} venda(s) aguardam as cobranças do iFood. Líquido, lucro e margem permanecem pendentes.`
    : "Aguardando as cobranças do iFood para conhecer o líquido, o lucro e a margem.";
}
