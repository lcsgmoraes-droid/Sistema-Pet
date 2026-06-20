const PAYMENT_RETURN_MESSAGES = {
  success: {
    level: "success",
    title: "Pagamento aprovado",
    message:
      "Recebemos a confirmacao do Mercado Pago. A loja ja recebeu seu pedido e a lista abaixo sera atualizada automaticamente.",
  },
  pending: {
    level: "warning",
    title: "Pagamento em analise",
    message:
      "O Mercado Pago ainda esta confirmando o pagamento. Atualize seus pedidos em alguns instantes para acompanhar.",
  },
  failure: {
    level: "error",
    title: "Pagamento nao concluido",
    message: "Pagamento recusado ou cancelado. Voce pode tentar novamente pelo pedido.",
  },
};

export function readMercadoPagoPaymentReturn(search = "") {
  const params = new URLSearchParams(search);
  const rawStatus = String(
    params.get("payment_status") || params.get("collection_status") || params.get("status") || "",
  )
    .trim()
    .toLowerCase();
  const status = rawStatus === "approved" ? "success" : rawStatus;
  const config = PAYMENT_RETURN_MESSAGES[status];

  if (!config) {
    return null;
  }

  return {
    status,
    level: config.level,
    title: config.title,
    message: config.message,
    pedidoId: params.get("pedido_id") || params.get("external_reference") || "",
  };
}

export function stripMercadoPagoPaymentReturnParams(search = "") {
  const params = new URLSearchParams(search);
  [
    "payment_status",
    "collection_status",
    "pedido_id",
    "external_reference",
    "collection_id",
    "payment_id",
    "status",
    "merchant_order_id",
    "preference_id",
    "site_id",
    "processing_mode",
    "merchant_account_id",
    "payment_type",
  ].forEach((key) => params.delete(key));
  params.set("view", "pedidos");
  return params.toString();
}
