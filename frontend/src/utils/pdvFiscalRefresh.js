import { extrairCamposFiscaisVenda } from "./pdvFiscalStatus.js";

export async function atualizarSituacaoFiscalVenda(
  venda,
  { consultarIntNFe, sincronizarBling, buscarVenda },
) {
  if (
    !venda?.id ||
    String(venda.nfe_status || "")
      .trim()
      .toLowerCase() === "cancelada"
  ) {
    return venda;
  }

  const intnfe = Boolean(venda.nfe_correlation_id);
  if (!intnfe && !venda.nfe_bling_id) return venda;

  try {
    if (intnfe) await consultarIntNFe(venda.id);
    else await sincronizarBling(venda.id);

    // Recarrega a venda persistida: o emissor também pode liberar seu status comercial.
    return { ...(await buscarVenda(venda.id)), nfe_atualizacao_falhou: false };
  } catch {
    // A indisponibilidade do emissor não pode esconder a venda nem simular um cancelamento.
    return { ...venda, nfe_atualizacao_falhou: true };
  }
}

export function mesclarSituacaoFiscalVenda(vendaAtual, vendaConsultada) {
  if (String(vendaAtual?.id) !== String(vendaConsultada?.id)) return vendaAtual;
  if (vendaAtual.status === "cancelada" && vendaConsultada.status !== "cancelada")
    return vendaAtual;
  const documentoAtual =
    vendaAtual.nfe_correlation_id || vendaAtual.nfe_bling_id || vendaAtual.nfe_chave;
  const documentoConsultado =
    vendaConsultada.nfe_correlation_id || vendaConsultada.nfe_bling_id || vendaConsultada.nfe_chave;
  if (
    documentoAtual &&
    documentoAtual === documentoConsultado &&
    String(vendaAtual.nfe_status || "").toLowerCase() === "cancelada" &&
    String(vendaConsultada.nfe_status || "").toLowerCase() !== "cancelada"
  ) {
    return vendaAtual;
  }
  return {
    ...vendaAtual,
    ...extrairCamposFiscaisVenda(vendaConsultada),
    status: vendaConsultada.status,
    nfe_atualizacao_falhou: Boolean(vendaConsultada.nfe_atualizacao_falhou),
  };
}
