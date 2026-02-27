/**
 * Google Analytics 4 — Rastreamento do E-commerce
 *
 * Para ativar:
 *   1. Crie uma propriedade em analytics.google.com
 *   2. Copie o ID de medição (formato: G-XXXXXXXXXX)
 *   3. Adicione ao arquivo frontend/.env.production:
 *      VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX
 *   4. Faça o build: npm run build
 *
 * Enquanto o ID não está configurado, as funções não fazem nada.
 */

const GA_ID = import.meta.env.VITE_GA_MEASUREMENT_ID;

function gtag(...args) {
  if (!GA_ID || !window.gtag) return;
  window.gtag(...args);
}

/**
 * Rastreia mudança de tela dentro da loja.
 * @param {string} screenName - ex: 'loja', 'carrinho', 'checkout', 'conta', 'pedidos'
 */
export function trackPageView(screenName) {
  const titles = {
    loja: 'Loja',
    carrinho: 'Carrinho',
    checkout: 'Checkout',
    conta: 'Minha Conta',
    pedidos: 'Meus Pedidos',
  };
  gtag('event', 'page_view', {
    page_title: titles[screenName] || screenName,
    page_location: window.location.href,
  });
}

/**
 * Cliente abriu o detalhe de um produto.
 */
export function trackViewItem(product) {
  gtag('event', 'view_item', {
    currency: 'BRL',
    value: resolvePrice(product),
    items: [buildItem(product, 1)],
  });
}

/**
 * Produto adicionado ao carrinho.
 */
export function trackAddToCart(product) {
  gtag('event', 'add_to_cart', {
    currency: 'BRL',
    value: resolvePrice(product),
    items: [buildItem(product, 1)],
  });
}

/**
 * Cliente clicou em "Finalizar compra" (foi para a tela de checkout).
 */
export function trackBeginCheckout(cart) {
  gtag('event', 'begin_checkout', {
    currency: 'BRL',
    value: Number(cart?.total || 0),
    items: buildCartItems(cart),
  });
}

/**
 * Compra finalizada com sucesso.
 */
export function trackPurchase(result, cart) {
  gtag('event', 'purchase', {
    transaction_id: result?.pedido_id || '',
    currency: 'BRL',
    value: Number(cart?.total || 0),
    items: buildCartItems(cart),
  });
}

/**
 * Cliente abriu o carrinho.
 */
export function trackViewCart(cart) {
  gtag('event', 'view_cart', {
    currency: 'BRL',
    value: Number(cart?.total || 0),
    items: buildCartItems(cart),
  });
}

// ─── Funções auxiliares ────────────────────────────────────────────────────

function resolvePrice(product) {
  return Number(product?.preco_venda ?? product?.preco ?? product?.preco_unitario ?? 0);
}

function buildItem(product, quantity) {
  return {
    item_id: String(product?.id || product?.produto_id || ''),
    item_name: product?.nome || product?.name || '',
    price: resolvePrice(product),
    quantity: Number(quantity || 1),
  };
}

function buildCartItems(cart) {
  return (cart?.itens || []).map((item) => ({
    item_id: String(item.produto_id || ''),
    item_name: item.nome || '',
    price: Number(item.preco_unitario || 0),
    quantity: Number(item.quantidade || 1),
  }));
}
