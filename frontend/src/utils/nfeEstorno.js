import { textoRespostaFiscal } from "./pdvFiscalStatus.js";

export function normalizarStatusEstorno(valor) {
  const status = String(valor || "")
    .trim()
    .toLowerCase();
  return (
    {
      autorizada: "autorizado",
      rejeitada: "rejeitado",
      cancelada: "cancelado",
      denegada: "denegado",
    }[status] || status
  );
}

export function obterEstornoFiscal(dados = {}) {
  return (
    dados.estorno ||
    dados.nfe_estorno || {
      status: dados.nfe_estorno_status,
      numero: dados.nfe_estorno_numero,
      serie: dados.nfe_estorno_serie,
      protocolo: dados.nfe_estorno_protocolo,
    }
  );
}

export function obterSituacaoEstorno(dados = {}) {
  const estorno = obterEstornoFiscal(dados);
  const status = normalizarStatusEstorno(estorno.status);
  if (!status) return null;
  const configuracoes = {
    autorizado: { label: "NF-e de estorno autorizada", intent: "success" },
    enviando: { label: "Emissão do estorno em processamento", intent: "warning" },
    incerto: { label: "Resultado do estorno não confirmado", intent: "warning" },
    processando: { label: "Emissão do estorno em processamento", intent: "warning" },
    rejeitado: { label: "NF-e de estorno rejeitada", intent: "danger" },
    denegado: { label: "NF-e de estorno denegada", intent: "danger" },
    cancelado: { label: "NF-e de estorno cancelada", intent: "danger" },
    divergente: { label: "Estorno com divergência fiscal", intent: "danger" },
  };
  const config = configuracoes[status] || {
    label: "Estorno aguardando confirmação",
    intent: "warning",
  };
  return { ...config, status, estorno, detalhe: textoRespostaFiscal(estorno.motivo) };
}

export function notaPermiteAcompanharEstorno(nota = {}) {
  if (
    (nota.provedor || nota.nfe_provider) === "intnfe" &&
    nota.venda_id &&
    obterSituacaoEstorno(nota)
  )
    return true;
  return Boolean(
    (nota.provedor || nota.nfe_provider) === "intnfe" &&
    nota.venda_id &&
    ["cancelada", "cancelado"].includes(String(nota.venda_status || "").toLowerCase()) &&
    (Number(nota.modelo || nota.nfe_modelo) === 65 || (nota.tipo || nota.nfe_tipo) === "nfce") &&
    String(nota.nfe_status || nota.status || "").toLowerCase() === "autorizada" &&
    (nota.pendencia_fiscal_cancelamento === true || obterSituacaoEstorno(nota)),
  );
}

export function podeEmitirEstorno(dados, { declarado, motivo, envioIniciado = false }) {
  const previa = dados?.previa;
  return Boolean(
    dados?.elegivel === true &&
    !(dados.bloqueios || []).length &&
    previa &&
    Number(previa.modelo) === 55 &&
    previa.tipo_operacao === "entrada" &&
    previa.finalidade === "ajuste" &&
    /^\d{44}$/.test(String(previa.original?.chave || "")) &&
    !normalizarStatusEstorno(obterEstornoFiscal(dados).status) &&
    !obterEstornoFiscal(dados).id &&
    !obterEstornoFiscal(dados).correlation_id &&
    declarado &&
    String(motivo || "").trim().length >= 15 &&
    String(motivo || "").trim().length <= 500 &&
    !envioIniciado,
  );
}

export function documentosEstornoDisponiveis(dados = {}) {
  const estorno = obterEstornoFiscal(dados);
  return (
    normalizarStatusEstorno(estorno.status) === "autorizado" &&
    estorno.xml_validado === true &&
    /^\d{15}$/.test(String(estorno.protocolo || ""))
  );
}

export function mensagemErroEstorno(error) {
  const dados = error?.response?.data?.detail || error?.response?.data;
  const codigo = textoRespostaFiscal(dados?.codigo || dados?.code);
  const motivo =
    textoRespostaFiscal(dados || error?.message) ||
    "Não foi possível confirmar o resultado do estorno. Consulte a situação antes de tentar novamente.";
  return [codigo ? `Código ${codigo}` : "", motivo].filter(Boolean).join(" — ");
}
