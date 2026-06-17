import { formatMoneyBRL } from "../../utils/formatters.js";

export const STORAGE_TOKEN_KEY = "ecommerce_customer_token";
export const STORAGE_ORDERS_KEY = "ecommerce_customer_orders";
export const STORAGE_ADDRESS_KEY = "ecommerce_customer_address";
export const STORAGE_GUEST_CART_KEY = "ecommerce_guest_cart";
export const STORAGE_WISHLIST_KEY = "ecommerce_wishlist_products";
export const STORAGE_NOTIFY_KEY = "ecommerce_notify_requests";

const configuredApiUrl = import.meta.env?.VITE_API_URL;

export const DEFAULT_CATALOG_LIMIT = 24;
export const DEFAULT_CATALOG_ORDER = "relevancia";

export const EMPTY_CART = { pedido_id: null, itens: [], subtotal: 0, total: 0 };

export const EMPTY_ADDRESS_FIELDS = {
  cep: "",
  endereco: "",
  numero: "",
  complemento: "",
  bairro: "",
  cidade: "",
  estado: "",
};

export const BANNERS = [
  {
    bg: "linear-gradient(135deg, #f97316 0%, #ea580c 60%, #c2410c 100%)",
    title: "Compre e receba no mesmo dia!",
    sub: "Pedidos realizados atÃ© as 16h",
    emoji: "ðŸš€",
  },
  {
    bg: "linear-gradient(135deg, #10b981 0%, #059669 60%, #047857 100%)",
    title: "Retire na loja",
    sub: "Super simples e sem custo de frete!",
    emoji: "ðŸª",
  },
  {
    bg: "linear-gradient(135deg, #f59e0b 0%, #d97706 60%, #b45309 100%)",
    title: "As melhores raÃ§Ãµes em Prudente",
    sub: "Cachorros, gatos, pÃ¡ssaros e mais ðŸ¾",
    emoji: "ðŸ¶",
  },
];

export function formatCurrency(value) {
  return formatMoneyBRL(value);
}

export function formatDateTime(value) {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(parsed);
}

export function resolveProductPrice(product) {
  if (product?.promocao_ativa && product?.preco_promocional != null) {
    return Number(product.preco_promocional ?? 0);
  }
  return Number(product?.preco_venda ?? product?.preco ?? 0);
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
  if (product?.promocao_origem !== "validade") return null;
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
  const digits = String(cep || "").replace(/\D+/g, "");
  if (digits.length !== 8) return null;

  try {
    const response = await fetch(`https://viacep.com.br/ws/${digits}/json/`);
    if (!response.ok) return null;
    const data = await response.json();
    if (data?.erro) return null;
    return {
      cep: digits,
      endereco: data?.logradouro || "",
      bairro: data?.bairro || "",
      cidade: data?.localidade || "",
      estado: data?.uf || "",
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
  if (!url || typeof url !== "string") return "";
  if (/^https?:\/\//i.test(url)) return url;

  const normalizedPath = url.startsWith("/") ? url : `/${url}`;
  if (configuredApiUrl && /^https?:\/\//i.test(configuredApiUrl)) {
    const backendBase = configuredApiUrl.replace(/\/api\/?$/, "").replace(/\/$/, "");
    return `${backendBase}${normalizedPath}`;
  }

  if (import.meta.env?.DEV) {
    return `http://127.0.0.1:8000${normalizedPath}`;
  }

  if (typeof window === "undefined") {
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

export function normalizeCatalogPayload(payload) {
  const items = normalizeProductPayload(payload);
  return {
    items,
    total: Number(payload?.total ?? items.length) || 0,
    offset: Number(payload?.offset ?? 0) || 0,
    limit: Number(payload?.limit ?? DEFAULT_CATALOG_LIMIT) || DEFAULT_CATALOG_LIMIT,
    categories: Array.isArray(payload?.categorias) ? payload.categorias : [],
  };
}

export function buildCatalogCategories(products) {
  const all = products
    .map((item) => item?.categoria_nome || item?.categoria || "Sem categoria")
    .filter(Boolean);

  return ["todas", ...Array.from(new Set(all))];
}

export function formatCatalogCategoryLabel(value) {
  const text = String(value || "").trim();
  if (!text) return "Sem categoria";
  const parts = text
    .split(/>>|>|\/|\\/)
    .map((part) => part.trim())
    .filter(Boolean);
  return parts.at(-1) || text;
}

export function buildCatalogCategoryOptions({ categories = [], products = [] } = {}) {
  if (Array.isArray(categories) && categories.length > 0) {
    const normalized = categories
      .filter((item) => item?.id !== undefined && item?.id !== null)
      .map((item) => {
        const rawLabel = item?.nome || item?.label || "Sem categoria";
        return {
          id: String(item.id),
          value: String(item.id),
          label: formatCatalogCategoryLabel(rawLabel),
          rawLabel,
          total: Number(item?.total ?? 0) || 0,
        };
      });
    const total = normalized.reduce((sum, item) => sum + item.total, 0);
    return [{ id: "todas", value: "todas", label: "Todas as categorias", total }, ...normalized];
  }

  const counts = new Map();
  products.forEach((item) => {
    const rawLabel = item?.categoria_nome || item?.categoria || "Sem categoria";
    const key =
      item?.categoria_id !== undefined && item?.categoria_id !== null
        ? String(item.categoria_id)
        : rawLabel;
    const current = counts.get(key) || { rawLabel, total: 0 };
    counts.set(key, { rawLabel: current.rawLabel || rawLabel, total: current.total + 1 });
  });

  return [
    { id: "todas", value: "todas", label: "Todas as categorias", total: products.length },
    ...Array.from(counts.entries()).map(([id, item]) => ({
      id,
      value: id,
      label: formatCatalogCategoryLabel(item.rawLabel),
      rawLabel: item.rawLabel,
      total: item.total,
    })),
  ];
}

export function normalizeCatalogOrder(order) {
  const value = String(order || DEFAULT_CATALOG_ORDER)
    .trim()
    .toLowerCase();
  if (value === "relevancia" || value === "prontos") return "prontos";
  if (value === "nome") return "nome_asc";
  if (["nome_asc", "menor_preco", "maior_preco"].includes(value)) return value;
  return "prontos";
}

export function buildCatalogQueryParams({
  tenant,
  search = "",
  category = "todas",
  order = DEFAULT_CATALOG_ORDER,
  page = 1,
  limit = DEFAULT_CATALOG_LIMIT,
  channel,
} = {}) {
  const safeLimit = Math.max(1, Math.min(500, Number(limit) || DEFAULT_CATALOG_LIMIT));
  const safePage = Math.max(1, Number(page) || 1);
  const categoryValue = typeof category === "object" ? category?.value : category;
  const params = {
    tenant,
    ordenacao: normalizeCatalogOrder(order),
    offset: (safePage - 1) * safeLimit,
    limit: safeLimit,
  };

  const trimmedSearch = String(search || "").trim();
  if (trimmedSearch) params.busca = trimmedSearch;

  if (categoryValue && categoryValue !== "todas") {
    const numericCategory = Number(categoryValue);
    if (Number.isFinite(numericCategory)) {
      params.categoria_id = numericCategory;
    }
  }

  if (channel) params.canal = channel;
  return params;
}

export function buildPaginationWindow({
  total = 0,
  limit = DEFAULT_CATALOG_LIMIT,
  page = 1,
  siblingCount = 1,
} = {}) {
  const safeTotal = Math.max(0, Number(total) || 0);
  const safeLimit = Math.max(1, Number(limit) || DEFAULT_CATALOG_LIMIT);
  const totalPages = safeTotal > 0 ? Math.ceil(safeTotal / safeLimit) : 0;
  const safePage = totalPages > 0 ? Math.min(Math.max(1, Number(page) || 1), totalPages) : 1;

  if (totalPages === 0) {
    return {
      total: safeTotal,
      limit: safeLimit,
      page: safePage,
      totalPages,
      startItem: 0,
      endItem: 0,
      pages: [],
      hasPrevious: false,
      hasNext: false,
    };
  }

  const pages = new Set([1, totalPages]);
  if (totalPages <= 7) {
    for (let item = 1; item <= totalPages; item += 1) pages.add(item);
  } else {
    for (let item = safePage - siblingCount; item <= safePage + siblingCount; item += 1) {
      if (item >= 1 && item <= totalPages) pages.add(item);
    }
  }

  return {
    total: safeTotal,
    limit: safeLimit,
    page: safePage,
    totalPages,
    startItem: (safePage - 1) * safeLimit + 1,
    endItem: Math.min(safePage * safeLimit, safeTotal),
    pages: Array.from(pages).sort((left, right) => left - right),
    hasPrevious: safePage > 1,
    hasNext: safePage < totalPages,
  };
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
    },
  );
}

export function filterCatalogProducts(
  products,
  {
    search = "",
    categoria = "todas",
    somenteComEstoque = false,
    somenteComImagem = false,
    ordenacaoCatalogo = "prontos",
  } = {},
) {
  const query = search.trim().toLowerCase();
  const sorted = products
    .filter((item) => {
      const nome = String(item?.nome || "").toLowerCase();
      const codigo = String(item?.codigo || "").toLowerCase();
      const categoriaNome = item?.categoria_nome || item?.categoria || "Sem categoria";
      const hasImage = getProductImages(item).length > 0;
      const inStock = !isProductOutOfStock(item);
      const matchesSearch = !query || nome.includes(query) || codigo.includes(query);
      const matchesCategoria = categoria === "todas" || categoriaNome === categoria;
      const matchesStock = !somenteComEstoque || inStock;
      const matchesImage = !somenteComImagem || hasImage;
      return matchesSearch && matchesCategoria && matchesStock && matchesImage;
    })
    .slice();

  sorted.sort((left, right) => {
    const leftName = String(left?.nome || "");
    const rightName = String(right?.nome || "");
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

    if (ordenacaoCatalogo === "menor_preco") {
      return leftPrice - rightPrice || leftName.localeCompare(rightName, "pt-BR");
    }

    if (ordenacaoCatalogo === "maior_preco") {
      return rightPrice - leftPrice || leftName.localeCompare(rightName, "pt-BR");
    }

    if (ordenacaoCatalogo === "nome" || ordenacaoCatalogo === "nome_asc") {
      return leftName.localeCompare(rightName, "pt-BR");
    }

    return (
      rightReadyScore - leftReadyScore ||
      Number(rightStock || 0) - Number(leftStock || 0) ||
      leftName.localeCompare(rightName, "pt-BR")
    );
  });

  return sorted;
}

export function buildActiveBanners(tenantContext) {
  const urls = [
    tenantContext?.banner_1_url,
    tenantContext?.banner_2_url,
    tenantContext?.banner_3_url,
  ].filter(Boolean);

  if (urls.length > 0) return urls.map((url) => ({ type: "image", url }));
  return BANNERS;
}

export function isCustomerProfileComplete(customer) {
  const fullName = String(customer?.nome || "").trim();
  const hasFullName = fullName.includes(" ");
  const hasPhone = String(customer?.telefone || "").trim().length >= 8;
  const hasCpf = String(customer?.cpf || "").replace(/\D+/g, "").length >= 11;
  const hasAddress = String(customer?.endereco || "").trim().length > 3;
  return hasFullName && hasPhone && hasCpf && hasAddress;
}

export function buildProductMap(products) {
  return Object.fromEntries(products.map((product) => [product.id, product]));
}

export function resolveStoreDisplayName({ tenantContext, storefrontRef }) {
  const backendName = tenantContext?.name || "";
  if (backendName && !isLikelyCorruptedText(backendName)) {
    return backendName;
  }
  if (storefrontRef) {
    return humanizeSlug(storefrontRef);
  }
  return "Loja online";
}

export function buildCustomerProfileForm(customer) {
  const deliveryDetails = customer?.endereco_entrega_detalhado || {};

  return {
    nome: customer?.nome || "",
    telefone: customer?.telefone || "",
    cpf: customer?.cpf || "",
    cep: customer?.cep || "",
    endereco: customer?.endereco || "",
    numero: customer?.numero || "",
    complemento: customer?.complemento || "",
    bairro: customer?.bairro || "",
    cidade: customer?.cidade || "",
    estado: customer?.estado || "",
    endereco_entrega: customer?.endereco_entrega || "",
    usar_endereco_entrega_diferente: Boolean(customer?.usar_endereco_entrega_diferente),
    entrega_nome: deliveryDetails?.entrega_nome || "",
    entrega_cep: deliveryDetails?.entrega_cep || "",
    entrega_endereco: deliveryDetails?.entrega_endereco || "",
    entrega_numero: deliveryDetails?.entrega_numero || "",
    entrega_complemento: deliveryDetails?.entrega_complemento || "",
    entrega_bairro: deliveryDetails?.entrega_bairro || "",
    entrega_cidade: deliveryDetails?.entrega_cidade || "",
    entrega_estado: deliveryDetails?.entrega_estado || "",
  };
}

export function buildCustomerAddressFields(customer) {
  const deliveryDetails = customer?.endereco_entrega_detalhado || {};
  const useDeliveryAddress = Boolean(customer?.usar_endereco_entrega_diferente);

  return {
    cep: useDeliveryAddress
      ? deliveryDetails?.entrega_cep || customer?.cep || ""
      : customer?.cep || "",
    endereco: useDeliveryAddress
      ? deliveryDetails?.entrega_endereco || customer?.endereco || ""
      : customer?.endereco || "",
    numero: useDeliveryAddress
      ? deliveryDetails?.entrega_numero || customer?.numero || ""
      : customer?.numero || "",
    complemento: useDeliveryAddress
      ? deliveryDetails?.entrega_complemento || customer?.complemento || ""
      : customer?.complemento || "",
    bairro: useDeliveryAddress
      ? deliveryDetails?.entrega_bairro || customer?.bairro || ""
      : customer?.bairro || "",
    cidade: useDeliveryAddress
      ? deliveryDetails?.entrega_cidade || customer?.cidade || ""
      : customer?.cidade || "",
    estado: useDeliveryAddress
      ? deliveryDetails?.entrega_estado || customer?.estado || ""
      : customer?.estado || "",
  };
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
    if (typeof parsed === "object" && parsed !== null) {
      return {
        ...EMPTY_ADDRESS_FIELDS,
        ...parsed,
      };
    }
    return {
      ...EMPTY_ADDRESS_FIELDS,
      endereco: String(raw || ""),
    };
  } catch {
    const legacyRaw = localStorage.getItem(STORAGE_ADDRESS_KEY) || "";
    return {
      ...EMPTY_ADDRESS_FIELDS,
      endereco: legacyRaw,
    };
  }
}

export function buildAddressText(fields) {
  const rua = [fields.endereco, fields.numero].filter(Boolean).join(", ");
  const bairro = fields.bairro ? `Bairro: ${fields.bairro}` : "";
  const cidadeUf = [fields.cidade, fields.estado].filter(Boolean).join("/");
  const cep = fields.cep ? `CEP: ${fields.cep}` : "";
  const complemento = fields.complemento ? `Compl.: ${fields.complemento}` : "";

  return [rua, bairro, cidadeUf, cep, complemento].filter(Boolean).join(" | ");
}

export function getProductImages(product) {
  const images = [];
  if (product?.imagem_principal) {
    images.push(resolveMediaUrl(product.imagem_principal));
  }

  if (Array.isArray(product?.imagens)) {
    product.imagens.forEach((item) => {
      if (typeof item === "string" && item.trim()) {
        images.push(resolveMediaUrl(item.trim()));
      } else if (item?.url && typeof item.url === "string") {
        images.push(resolveMediaUrl(item.url.trim()));
      }
    });
  }

  return Array.from(new Set(images.filter(Boolean)));
}

export function isLikelyCorruptedText(value) {
  const text = String(value || "");
  if (!text) return false;
  return text.includes("??") || text.includes("ï¿½") || /\?{2,}/.test(text);
}

export function humanizeSlug(slug) {
  return String(slug || "")
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function extractApiErrorMessage(err, fallback) {
  const data = err?.response?.data;
  const detail = data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "string" && first.trim()) {
      return first;
    }
    if (typeof first?.msg === "string" && first.msg.trim()) {
      return first.msg;
    }
  }

  if (Array.isArray(data?.details) && data.details.length > 0) {
    const first = data.details[0];
    if (typeof first === "string" && first.trim()) {
      return first;
    }
    if (typeof first?.msg === "string" && first.msg.trim()) {
      return first.msg;
    }
  }

  if (typeof data?.message === "string" && data.message.trim()) {
    return data.message;
  }

  return fallback;
}
