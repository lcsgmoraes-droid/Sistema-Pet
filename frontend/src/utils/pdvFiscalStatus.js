const CAMPOS_FISCAIS_VENDA = [
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
  return CAMPOS_FISCAIS_VENDA.some((campo) => {
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
  if (venda.nfe_codigo_erro) detalhes.push(`Código ${venda.nfe_codigo_erro}`);
  if (venda.nfe_motivo_rejeicao) detalhes.push(String(venda.nfe_motivo_rejeicao));

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

export function rotaNotaFiscalVenda(venda = {}) {
  if (!temDocumentoFiscalVenda(venda)) return null;

  const parametros = new URLSearchParams({ abrir: "1" });
  if (venda.nfe_numero) parametros.set("busca", String(venda.nfe_numero));
  if (venda.id) parametros.set("venda_id", String(venda.id));

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
