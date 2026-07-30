/**
 * Analytics da loja: envia eventos anônimos ao CorePet e, quando configurado,
 * também ao Google Analytics 4.
 */

const GA_ID = import.meta.env.VITE_GA_MEASUREMENT_ID;
const SESSION_KEY = "corepet_ecommerce_analytics_session";
let analyticsContext = { tenant: "", channel: "ecommerce" };

function getSessionId() {
  try {
    let value = localStorage.getItem(SESSION_KEY);
    if (!value) {
      value = window.crypto?.randomUUID?.() || `session-${Date.now()}-${Math.random()}`;
      value = value.replace(/[^A-Za-z0-9._-]/g, "");
      localStorage.setItem(SESSION_KEY, value);
    }
    return value;
  } catch {
    return `session-${Date.now()}`;
  }
}

export function setEcommerceAnalyticsContext({ tenant, channel = "ecommerce" } = {}) {
  analyticsContext = {
    tenant: String(tenant || ""),
    channel: channel === "app" ? "app" : "ecommerce",
  };
}

function gtag(...args) {
  if (!GA_ID || !window.gtag) return;
  window.gtag(...args);
}

function sendInternalEvent(eventName, data = {}) {
  if (!analyticsContext.tenant) return;
  const query = new URLSearchParams({ tenant: analyticsContext.tenant });
  const payload = {
    event_name: eventName,
    session_id: getSessionId(),
    channel: analyticsContext.channel,
    path: `${window.location.pathname}${window.location.search}`.slice(0, 300),
    product_id: data.productId || undefined,
    pedido_id: data.pedidoId || undefined,
    value: Number.isFinite(Number(data.value)) ? Number(data.value) : undefined,
    extra_data: data.extraData || undefined,
  };

  void fetch(`/api/ecommerce/events?${query.toString()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {});
}

export function trackPageView(screenName) {
  const titles = {
    loja: "Loja",
    carrinho: "Carrinho",
    checkout: "Checkout",
    conta: "Minha Conta",
    pedidos: "Meus Pedidos",
  };
  gtag("event", "page_view", {
    page_title: titles[screenName] || screenName,
    page_location: window.location.href,
  });
  sendInternalEvent("page_view", { extraData: { screen_name: screenName } });
}

export function trackSearch(term) {
  const searchTerm = String(term || "")
    .trim()
    .slice(0, 100);
  if (!searchTerm) return;
  gtag("event", "search", { search_term: searchTerm });
  sendInternalEvent("search", { extraData: { search_term: searchTerm } });
}

export function trackViewItem(product) {
  gtag("event", "view_item", {
    currency: "BRL",
    value: resolvePrice(product),
    items: [buildItem(product, 1)],
  });
  sendInternalEvent("view_item", {
    productId: product?.id,
    value: resolvePrice(product),
  });
}

export function trackAddToCart(product) {
  gtag("event", "add_to_cart", {
    currency: "BRL",
    value: resolvePrice(product),
    items: [buildItem(product, 1)],
  });
  sendInternalEvent("add_to_cart", {
    productId: product?.id,
    value: resolvePrice(product),
  });
}

export function trackBeginCheckout(cart) {
  gtag("event", "begin_checkout", {
    currency: "BRL",
    value: Number(cart?.total || 0),
    items: buildCartItems(cart),
  });
  sendInternalEvent("begin_checkout", { value: Number(cart?.total || 0) });
}

export function trackCheckoutSubmitted(result, cart) {
  sendInternalEvent("checkout_submitted", {
    pedidoId: result?.pedido_id,
    value: Number(result?.total ?? cart?.total ?? 0),
  });
}

export function trackPurchase(result, cart) {
  const value = Number(result?.total ?? cart?.total ?? 0);
  gtag("event", "purchase", {
    transaction_id: result?.pedido_id || "",
    currency: "BRL",
    value,
    items: buildCartItems(cart),
  });
  sendInternalEvent("purchase", { pedidoId: result?.pedido_id, value });
}

export function trackViewCart(cart) {
  gtag("event", "view_cart", {
    currency: "BRL",
    value: Number(cart?.total || 0),
    items: buildCartItems(cart),
  });
  sendInternalEvent("view_cart", { value: Number(cart?.total || 0) });
}

function resolvePrice(product) {
  return Number(
    product?.preco_promocional ??
      product?.preco_venda ??
      product?.preco ??
      product?.preco_unitario ??
      0,
  );
}

function buildItem(product, quantity) {
  return {
    item_id: String(product?.id || product?.produto_id || ""),
    item_name: product?.nome || product?.name || "",
    item_brand: product?.marca_nome || undefined,
    item_category: product?.categoria_nome || undefined,
    price: resolvePrice(product),
    quantity: Number(quantity || 1),
  };
}

function buildCartItems(cart) {
  return (cart?.itens || []).map((item) => buildItem(item, item.quantidade));
}
