const APP_PAYMENT_STATUS_ALIASES = {
  approved: "success",
};

function cleanParam(value) {
  return String(value || "").trim();
}

function paymentStatusFromParams(params) {
  const rawStatus = cleanParam(params.get("payment_status") || params.get("status")).toLowerCase();
  return APP_PAYMENT_STATUS_ALIASES[rawStatus] || rawStatus || "pending";
}

function appendPaymentReturnParams(baseUrl, { paymentStatus, pedidoId, loja }) {
  const params = new URLSearchParams();
  if (paymentStatus) params.set("payment_status", paymentStatus);
  if (pedidoId) params.set("pedido_id", pedidoId);
  if (loja) params.set("loja", loja);
  const query = params.toString();
  return `${baseUrl}${query ? `?${query}` : ""}`;
}

export function readAppPaymentReturnParams(search = "") {
  const params = new URLSearchParams(search);
  return {
    paymentStatus: paymentStatusFromParams(params),
    pedidoId: cleanParam(params.get("pedido_id")),
    loja: cleanParam(params.get("loja") || params.get("tenant") || params.get("store")),
  };
}

export function buildAppPaymentReturnLinks(returnParams = {}) {
  const payload = {
    paymentStatus: cleanParam(returnParams.paymentStatus || "pending"),
    pedidoId: cleanParam(returnParams.pedidoId),
    loja: cleanParam(returnParams.loja),
  };
  const deepLink = appendPaymentReturnParams("corepet://app/pedidos", payload);
  const androidIntentPath = appendPaymentReturnParams("intent://app/pedidos", payload);

  return {
    deepLink,
    androidIntentLink: `${androidIntentPath}#Intent;scheme=corepet;package=br.com.corepet.app;end`,
    retryLink: deepLink,
  };
}

export function selectAppPaymentReturnOpenLink(links, userAgent = "") {
  if (/Android/i.test(String(userAgent || ""))) {
    return links.androidIntentLink;
  }
  return links.deepLink;
}
