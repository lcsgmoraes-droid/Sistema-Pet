import { formatMoneyBRL } from '../../utils/formatters.js';

export const STORAGE_TOKEN_KEY = 'ecommerce_customer_token';
export const STORAGE_ORDERS_KEY = 'ecommerce_customer_orders';
export const STORAGE_ADDRESS_KEY = 'ecommerce_customer_address';
export const STORAGE_GUEST_CART_KEY = 'ecommerce_guest_cart';
export const STORAGE_WISHLIST_KEY = 'ecommerce_wishlist_products';
export const STORAGE_NOTIFY_KEY = 'ecommerce_notify_requests';

const configuredApiUrl = import.meta.env?.VITE_API_URL;

export const EMPTY_CART = { pedido_id: null, itens: [], subtotal: 0, total: 0 };

export const EMPTY_ADDRESS_FIELDS = {
  cep: '',
  endereco: '',
  numero: '',
  complemento: '',
  bairro: '',
  cidade: '',
  estado: '',
};

export const BANNERS = [
  {
    bg: 'linear-gradient(135deg, #f97316 0%, #ea580c 60%, #c2410c 100%)',
    title: 'Compre e receba no mesmo dia!',
    sub: 'Pedidos realizados atÃ© as 16h',
    emoji: 'ðŸš€',
  },
  {
    bg: 'linear-gradient(135deg, #10b981 0%, #059669 60%, #047857 100%)',
    title: 'Retire na loja',
    sub: 'Super simples e sem custo de frete!',
    emoji: 'ðŸª',
  },
  {
    bg: 'linear-gradient(135deg, #f59e0b 0%, #d97706 60%, #b45309 100%)',
    title: 'As melhores raÃ§Ãµes em Prudente',
    sub: 'Cachorros, gatos, pÃ¡ssaros e mais ðŸ¾',
    emoji: 'ðŸ¶',
  },
];

export function formatCurrency(value) {
  return formatMoneyBRL(value);
}

export function formatDateTime(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '-';
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(parsed);
}

export function resolveProductPrice(product) {
  if (product?.promocao_ativa && product?.preco_promocional != null) {
    return Number(product.preco_promocional ?? 0);
  }
  return Number(
    product?.preco_venda ??
      product?.preco ??
      0
  );
}

export function resolveOriginalProductPrice(product) {
  return Number(product?.preco_venda ?? product?.preco ?? 0);
}

export function hasPromotionalPrice(product) {
  return (
    Boolean(product?.promocao_ativa) &&
    Number(product?.preco_promocional ?? 0) > 0 &&
    Number(product?.preco_promocional ?? 0) < resolveOriginalProductPrice(product)
  );
}

export function resolveValidityPromotionText(product) {
  const promocaoValidade = product?.promocao_validade;
  if (!promocaoValidade?.ativa) return "";
  const quantidade = Number(promocaoValidade?.quantidade_promocional ?? 0);
  if (!Number.isFinite(quantidade) || quantidade <= 0) return "";
  const quantidadeLabel = Number.isInteger(quantidade)
    ? quantidade
    : quantidade.toFixed(2).replace(".", ",");
  return `Ate ${quantidadeLabel} unid. desse lote por esse preco`;
}

export function resolveValidityPromotionLimit(product) {
  const limite = Number(product?.promocao_validade?.quantidade_promocional ?? 0);
  if (product?.promocao_origem !== 'validade') return null;
  return Number.isFinite(limite) && limite > 0 ? limite : null;
}

export function resolveProductStock(product) {
  const currentStock = Number(product?.estoque_atual);

  if (Number.isFinite(currentStock)) {
    return currentStock;
  }

  const fallbackStock = Number(product?.estoque ?? 0);
  if (Number.isFinite(fallbackStock)) {
    return fallbackStock;
  }

  return Number.POSITIVE_INFINITY;
}

export function isProductOutOfStock(product) {
  const stock = resolveProductStock(product);
  return Number.isFinite(stock) && stock <= 0;
}

export async function fetchAddressByCep(cep) {
  const digits = String(cep || '').replace(/\D+/g, '');
  if (digits.length !== 8) return null;

  try {
    const response = await fetch(`https://viacep.com.br/ws/${digits}/json/`);
    if (!response.ok) return null;
    const data = await response.json();
    if (data?.erro) return null;
    return {
      cep: digits,
      endereco: data?.logradouro || '',
      bairro: data?.bairro || '',
      cidade: data?.localidade || '',
      estado: data?.uf || '',
    };
  } catch {
    return null;
  }
}

export function buildIdempotencyKey() {
  if (window?.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function resolveMediaUrl(url) {
  if (!url || typeof url !== 'string') return '';
  if (/^https?:\/\//i.test(url)) return url;

  const normalizedPath = url.startsWith('/') ? url : `/${url}`;
  if (configuredApiUrl && /^https?:\/\//i.test(configuredApiUrl)) {
    const backendBase = configuredApiUrl.replace(/\/api\/?$/, '').replace(/\/$/, '');
    return `${backendBase}${normalizedPath}`;
  }

  if (import.meta.env?.DEV) {
    return `http://127.0.0.1:8000${normalizedPath}`;
  }

  if (typeof window === 'undefined') {
    return normalizedPath;
  }

  return `${window.location.origin}${normalizedPath}`;
}

export function normalizeProductPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.itens)) return payload.itens;
  if (Array.isArray(payload?.produtos)) return payload.produtos;
  return [];
}

export function buildCatalogCategories(products) {
  const all = products
    .map((item) => item?.categoria_nome || item?.categoria || 'Sem categoria')
    .filter(Boolean);

  return ['todas', ...Array.from(new Set(all))];
}

export function calculateCatalogMetrics(products) {
  return products.reduce(
    (acc, item) => {
      const hasImage = getProductImages(item).length > 0;
      const inStock = !isProductOutOfStock(item);

      if (hasImage) acc.comImagem += 1;
      if (inStock) acc.emEstoque += 1;
      if (hasImage && inStock) acc.prontos += 1;

      return acc;
    },
    {
      total: products.length,
      comImagem: 0,
      emEstoque: 0,
      prontos: 0,
    }
  );
}

export function filterCatalogProducts(
  products,
  {
    search = '',
    categoria = 'todas',
    somenteComEstoque = false,
    somenteComImagem = false,
    ordenacaoCatalogo = 'prontos',
  } = {}
) {
  const query = search.trim().toLowerCase();
  const sorted = products
    .filter((item) => {
      const nome = String(item?.nome || '').toLowerCase();
      const codigo = String(item?.codigo || '').toLowerCase();
      const categoriaNome = item?.categoria_nome || item?.categoria || 'Sem categoria';
      const hasImage = getProductImages(item).length > 0;
      const inStock = !isProductOutOfStock(item);
      const matchesSearch = !query || nome.includes(query) || codigo.includes(query);
      const matchesCategoria = categoria === 'todas' || categoriaNome === categoria;
      const matchesStock = !somenteComEstoque || inStock;
      const matchesImage = !somenteComImagem || hasImage;
      return matchesSearch && matchesCategoria && matchesStock && matchesImage;
    })
    .slice();

  sorted.sort((left, right) => {
    const leftName = String(left?.nome || '');
    const rightName = String(right?.nome || '');
    const leftPrice = resolveProductPrice(left);
    const rightPrice = resolveProductPrice(right);
    const leftStock = resolveProductStock(left);
    const rightStock = resolveProductStock(right);
    const leftHasImage = getProductImages(left).length > 0;
    const rightHasImage = getProductImages(right).length > 0;
    const leftInStock = !isProductOutOfStock(left);
    const rightInStock = !isProductOutOfStock(right);
    const leftReadyScore = Number(leftInStock) * 2 + Number(leftHasImage);
    const rightReadyScore = Number(rightInStock) * 2 + Number(rightHasImage);

    if (ordenacaoCatalogo === 'menor_preco') {
      return leftPrice - rightPrice || leftName.localeCompare(rightName, 'pt-BR');
    }

    if (ordenacaoCatalogo === 'maior_preco') {
      return rightPrice - leftPrice || leftName.localeCompare(rightName, 'pt-BR');
    }

    if (ordenacaoCatalogo === 'nome') {
      return leftName.localeCompare(rightName, 'pt-BR');
    }

    return (
      rightReadyScore - leftReadyScore ||
      Number(rightStock || 0) - Number(leftStock || 0) ||
      leftName.localeCompare(rightName, 'pt-BR')
    );
  });

  return sorted;
}

export function getGuestCart() {
  try {
    const raw = localStorage.getItem(STORAGE_GUEST_CART_KEY);
    if (!raw) return { ...EMPTY_CART };
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed?.itens)) return { ...EMPTY_CART };
    const subtotal = Number(parsed?.subtotal || 0);
    const total = Number(parsed?.total || 0);
    return {
      pedido_id: null,
      itens: parsed.itens,
      subtotal,
      total,
    };
  } catch {
    return { ...EMPTY_CART };
  }
}

export function recalculateGuestCart(items) {
  const subtotal = items.reduce((acc, item) => {
    return acc + Number(item.preco_unitario || 0) * Number(item.quantidade || 0);
  }, 0);

  return {
    pedido_id: null,
    itens: items,
    subtotal,
    total: subtotal,
  };
}

export function getStoredAddressFields() {
  try {
    const raw = localStorage.getItem(STORAGE_ADDRESS_KEY);
    if (!raw) return { ...EMPTY_ADDRESS_FIELDS };
    const parsed = JSON.parse(raw);
    if (typeof parsed === 'object' && parsed !== null) {
      return {
        ...EMPTY_ADDRESS_FIELDS,
        ...parsed,
      };
    }
    return {
      ...EMPTY_ADDRESS_FIELDS,
      endereco: String(raw || ''),
    };
  } catch {
    const legacyRaw = localStorage.getItem(STORAGE_ADDRESS_KEY) || '';
    return {
      ...EMPTY_ADDRESS_FIELDS,
      endereco: legacyRaw,
    };
  }
}

export function buildAddressText(fields) {
  const rua = [fields.endereco, fields.numero].filter(Boolean).join(', ');
  const bairro = fields.bairro ? `Bairro: ${fields.bairro}` : '';
  const cidadeUf = [fields.cidade, fields.estado].filter(Boolean).join('/');
  const cep = fields.cep ? `CEP: ${fields.cep}` : '';
  const complemento = fields.complemento ? `Compl.: ${fields.complemento}` : '';

  return [rua, bairro, cidadeUf, cep, complemento].filter(Boolean).join(' | ');
}

export function getProductImages(product) {
  const images = [];
  if (product?.imagem_principal) {
    images.push(resolveMediaUrl(product.imagem_principal));
  }

  if (Array.isArray(product?.imagens)) {
    product.imagens.forEach((item) => {
      if (typeof item === 'string' && item.trim()) {
        images.push(resolveMediaUrl(item.trim()));
      } else if (item?.url && typeof item.url === 'string') {
        images.push(resolveMediaUrl(item.url.trim()));
      }
    });
  }

  return Array.from(new Set(images.filter(Boolean)));
}

export function isLikelyCorruptedText(value) {
  const text = String(value || '');
  if (!text) return false;
  return text.includes('??') || text.includes('ï¿½') || /\?{2,}/.test(text);
}

export function humanizeSlug(slug) {
  return String(slug || '')
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function extractApiErrorMessage(err, fallback) {
  const data = err?.response?.data;
  const detail = data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === 'string' && first.trim()) {
      return first;
    }
    if (typeof first?.msg === 'string' && first.msg.trim()) {
      return first.msg;
    }
  }

  if (Array.isArray(data?.details) && data.details.length > 0) {
    const first = data.details[0];
    if (typeof first === 'string' && first.trim()) {
      return first;
    }
    if (typeof first?.msg === 'string' && first.msg.trim()) {
      return first.msg;
    }
  }

  if (typeof data?.message === 'string' && data.message.trim()) {
    return data.message;
  }

  return fallback;
}
