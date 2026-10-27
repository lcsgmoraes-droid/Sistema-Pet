import { textoRespostaFiscal } from "../../../utils/pdvFiscalStatus.js";

export const FISCAL_BASE = "/integracoes/ecommerceai/fiscal/manage";
export const FISCAL_SCOPES = ["fiscal:prepare", "fiscal:issue", "fiscal:read"];
export const STATUS_FISCAIS = {
  blocked: "Com pendências",
  ready: "Pronto para emitir",
  processing: "Em processamento",
  unknown: "Sem confirmação",
  authorized: "Autorizada na SEFAZ",
  rejected: "Rejeitada",
  canceled: "Cancelada",
};
export const SCOPE_LABELS = {
  "catalog:read": "Consultar catálogo, preços, custos e estoque",
  "events:write": "Enviar eventos e indicadores",
  "fiscal:prepare": "Preparar pedidos para revisão fiscal",
  "fiscal:issue": "Solicitar emissão de NF-e",
  "fiscal:read": "Consultar notas e baixar XML/DANFE",
};

export function canIssueOrder(order) {
  return Boolean(
    order?.status === "ready" &&
    Array.isArray(order.blockers) &&
    !order.blockers.length &&
    Number.isInteger(order.source_revision) &&
    order.source_revision > 0 &&
    typeof order.payload_hash === "string" &&
    order.payload_hash.length > 0,
  );
}

export function accountPayload(form) {
  if (!form.seller_id?.trim()) throw new Error("Informe o Seller ID da conta Amazon.");
  const cnpj = String(form.emitter_cnpj || "").replaceAll(/\D/g, "");
  if (cnpj.length !== 14) throw new Error("Informe o CNPJ completo do emitente.");
  if (
    form.discount_policy &&
    !["source_discounts", "buyer_payment_total"].includes(form.discount_policy)
  )
    throw new Error("Selecione uma política de descontos válida.");
  if (form.discount_policy === "buyer_payment_total" && !form.discount_consent)
    throw new Error("Confirme a política que ajusta o desconto ao pagamento documentado.");
  return {
    channel: "amazon",
    seller_id: form.seller_id.trim(),
    marketplace_id: "A2Q3Y263D00KWC",
    emitter_cnpj: cnpj,
    discount_policy: form.discount_policy || "source_discounts",
    auto_issue_enabled: Boolean(form.auto_issue_enabled),
    active: form.active !== false,
  };
}

export async function fiscalError(error) {
  let data = error?.response?.data;
  if (typeof Blob !== "undefined" && data instanceof Blob) {
    try {
      data = JSON.parse(await data.text());
    } catch {
      data = null;
    }
  }
  if (Array.isArray(data?.detail))
    data = data.detail.map((item) => item.msg || item.message || "").join(" ");
  return (
    textoRespostaFiscal(data || error?.message) || "Não foi possível concluir a operação fiscal."
  );
}

export function formatFiscalDate(value) {
  if (!value) return "Ainda não ativada";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR");
}

export async function downloadFiscalDocument(api, order, kind) {
  const { data } = await api.get(`${FISCAL_BASE}/orders/${order.id}/${kind}`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `nfe-${String(order.numero || order.id).replaceAll(/[^\w-]/g, "")}.${kind === "xml" ? "xml" : "pdf"}`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
