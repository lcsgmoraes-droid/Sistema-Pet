import {
  MENSAGEM_SUPORTE_RESPONSAVEL_TECNICO,
  rejeicaoResponsavelTecnico,
} from "./fiscalRejectionGuidance.mjs";

const CAMPOS_DOCUMENTO_FISCAL = [
  "nfe_tipo",
  "nfe_modelo",
  "nfe_numero",
  "nfe_serie",
  "nfe_chave",
  "nfe_status",
  "nfe_provider",
  "nfe_correlation_id",
  "nfe_protocolo",
  "nfe_ambiente",
  "nfe_codigo_erro",
  "nfe_data_emissao",
  "nfe_data_autorizacao",
  "nfe_motivo_rejeicao",
  "nfe_bling_id",
];
const CAMPOS_FISCAIS_VENDA = [
  ...CAMPOS_DOCUMENTO_FISCAL,
  "nfe_cancelamento_status",
  "nfe_cancelamento_codigo",
  "nfe_cancelamento_motivo",
  "nfe_cancelamento_solicitado_em",
  "pendencia_fiscal_cancelamento",
];

const STATUS_FISCAL = {
  aguardando: { intent: "warning", label: "Aguardando" },
  autorizada: { intent: "success", label: "Autorizada" },
  cancelada: { intent: "danger", label: "Cancelada" },
  denegada: { intent: "danger", label: "Denegada" },
  emitida_danfe: { intent: "info", label: "Emitida" },
  enviando: { intent: "warning", label: "Enviando" },
  erro: { intent: "danger", label: "Com erro" },
  inconclusiva: { intent: "warning", label: "Inconclusiva" },
  inutilizada: { intent: "neutral", label: "Inutilizada" },
  pendente: { intent: "warning", label: "Pendente" },
  processando: { intent: "warning", label: "Processando" },
  rejeitada: { intent: "danger", label: "Rejeitada" },
};

function normalizar(valor) {
  return String(valor || "")
    .trim()
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replaceAll(/[^a-z0-9]+/g, "_")
    .replaceAll(/^_+|_+$/g, "");
}

function capitalizar(valor) {
  const texto = String(valor || "").trim();
  if (!texto) return "Situação não informada";
  return texto.charAt(0).toLocaleUpperCase("pt-BR") + texto.slice(1);
}

export function extrairCamposFiscaisVenda(venda = {}) {
  return Object.fromEntries(CAMPOS_FISCAIS_VENDA.map((campo) => [campo, venda[campo] ?? null]));
}

export function tipoDocumentoFiscalVenda(venda = {}) {
  const modelo = String(venda.nfe_modelo || "").trim();
  const tipo = normalizar(venda.nfe_tipo);
  if (modelo === "55" || tipo === "nfe") return "NF-e";
  if (modelo === "65" || tipo === "nfce") return "NFC-e";
  return "Nota fiscal";
}

export function temDocumentoFiscalVenda(venda = {}) {
  return CAMPOS_DOCUMENTO_FISCAL.some((campo) => {
    const valor = venda[campo];
    return valor !== null && valor !== undefined && String(valor).trim() !== "";
  });
}

export function obterSituacaoFiscalVenda(venda = {}) {
  if (!temDocumentoFiscalVenda(venda)) return null;

  const documento = tipoDocumentoFiscalVenda(venda);
  const numero = venda.nfe_numero ? String(venda.nfe_numero) : "";
  const status = normalizar(venda.nfe_status);
  const config = STATUS_FISCAL[status] || {
    intent: "info",
    label: capitalizar(String(venda.nfe_status || "").replaceAll("_", " ")),
  };
  const referencia = `${documento}${numero ? ` nº ${numero}` : ""}`;
  const detalhes = [];
  if (
    rejeicaoResponsavelTecnico({
      codigo: venda.nfe_codigo_erro,
      motivo: venda.nfe_motivo_rejeicao,
    })
  ) {
    detalhes.push(MENSAGEM_SUPORTE_RESPONSAVEL_TECNICO);
  } else {
    if (venda.nfe_codigo_erro) detalhes.push(`Código ${venda.nfe_codigo_erro}`);
    if (venda.nfe_motivo_rejeicao) detalhes.push(String(venda.nfe_motivo_rejeicao));
  }

  return {
    documento,
    numero,
    status,
    statusLabel: config.label,
    intent: config.intent,
    label: `${documento}${numero ? ` ${numero}` : ""}: ${config.label}`,
    titulo: `${referencia} — ${config.label}`,
    detalhe: detalhes.join(" — "),
  };
}

export function podeCancelarVenda(venda = {}) {
  const statusVenda = normalizar(venda.status);
  return Boolean(
    venda.id && ["aberta", "finalizada", "baixa_parcial", "pago_nf"].includes(statusVenda),
  );
}

export function temNotaFiscalAtiva(venda = {}) {
  const situacao = normalizar(venda.nfe_status);
  if (["cancelada", "cancelado"].includes(situacao)) return false;
  if (venda.pendencia_fiscal_cancelamento === true) return true;
  if (
    ["rejeitada", "rascunho", "denegada", "inutilizada"].includes(situacao) &&
    !venda.nfe_data_autorizacao
  )
    return false;
  if (
    normalizar(venda.status) === "pago_nf" ||
    [
      "autorizada",
      "emitida",
      "emitida_danfe",
      "aguardando",
      "pendente",
      "enviando",
      "processando",
      "inconclusiva",
      "contingencia",
    ].includes(situacao)
  )
    return true;
  return Boolean(
    venda.nfe_data_autorizacao ||
    venda.nfe_correlation_id ||
    venda.nfe_bling_id ||
    venda.nfe_protocolo,
  );
}

export function obterPendenciaCancelamentoFiscal(venda = {}) {
  if (!temNotaFiscalAtiva(venda)) return null;
  const status = normalizar(venda.nfe_cancelamento_status || venda.cancelamento_status);
  if (
    !["cancelada", "cancelado"].includes(normalizar(venda.status)) &&
    !venda.pendencia_fiscal_cancelamento &&
    !["pendente", "solicitado", "recusado"].includes(status)
  )
    return null;
  const codigo = textoRespostaFiscal(venda.nfe_cancelamento_codigo || venda.cancelamento_codigo);
  const motivo = textoRespostaFiscal(venda.nfe_cancelamento_motivo || venda.cancelamento_motivo);
  return {
    status: status || "pendente",
    label: status === "solicitado" ? "Cancelamento da nota em andamento" : "Nota a cancelar",
    intent: status === "recusado" ? "danger" : "warning",
    codigo,
    motivo,
    detalhe: [codigo ? `Código ${codigo}` : "", motivo].filter(Boolean).join(" — "),
  };
}

export function textoRespostaFiscal(valor) {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "string" || typeof valor === "number") {
    const texto = String(valor).trim();
    if (
      /<!doctype\s+html|<\/?(?:html|head|body|title|center|h1|script|style)\b/i.test(texto) ||
      /\b(?:502\s+bad gateway|503\s+service unavailable|504\s+gateway time.?out|Network Error|ECONNRESET|ECONNREFUSED|AxiosError|timeout of \d+ms exceeded)\b/i.test(
        texto,
      )
    ) {
      return "O serviço emissor está temporariamente indisponível. Consulte a situação da nota antes de tentar novamente.";
    }
    return texto;
  }
  if (Array.isArray(valor)) return valor.map(textoRespostaFiscal).filter(Boolean).join("; ");
  if (typeof valor === "object") {
    const partes = [
      "motivo",
      "mensagem",
      "message",
      "detail",
      "erro",
      "error",
      "xMotivo",
      "descricao",
    ]
      .map((campo) => textoRespostaFiscal(valor[campo]))
      .filter(Boolean);
    return [...new Set(partes)].join(" — ");
  }
  return "";
}

export function rotaNotaFiscalVenda(venda = {}) {
  if (!temDocumentoFiscalVenda(venda)) return null;

  const parametros = new URLSearchParams({ abrir: "1" });
  if (venda.nfe_numero) parametros.set("busca", String(venda.nfe_numero));
  if (venda.id) parametros.set("venda_id", String(venda.id));
  if (normalizar(venda.nfe_status) === "rejeitada") parametros.set("corrigir", "1");

  return `/notas-fiscais/saida?${parametros.toString()}`;
}

export function rotaDanfeFiscalVenda(venda = {}) {
  if (!venda.id || !temDocumentoFiscalVenda(venda)) return null;

  const provedor = normalizar(venda.nfe_provider);
  if (provedor === "intnfe" || venda.nfe_correlation_id) {
    return `/nfe/vendas/${venda.id}/danfe`;
  }
  if (venda.nfe_bling_id) {
    return `/nfe/${venda.nfe_bling_id}/danfe`;
  }
  return null;
}

export function podeImprimirDocumentoFiscalVenda(venda = {}) {
  const status = normalizar(venda.nfe_status);
  return Boolean(
    rotaDanfeFiscalVenda(venda) && (status === "autorizada" || status === "emitida_danfe"),
  );
}
