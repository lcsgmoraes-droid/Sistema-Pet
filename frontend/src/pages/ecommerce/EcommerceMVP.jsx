import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import ecommerceApi from '../../services/ecommerceApi';
import { api } from '../../services/api';
import {
  trackPageView,
  trackViewItem,
  trackAddToCart,
  trackBeginCheckout,
  trackPurchase,
  trackViewCart,
} from '../../services/analytics';

const STORAGE_TOKEN_KEY = 'ecommerce_customer_token';
const STORAGE_ORDERS_KEY = 'ecommerce_customer_orders';
const STORAGE_ADDRESS_KEY = 'ecommerce_customer_address';
const STORAGE_GUEST_CART_KEY = 'ecommerce_guest_cart';
const STORAGE_WISHLIST_KEY = 'ecommerce_wishlist_products';
const STORAGE_NOTIFY_KEY = 'ecommerce_notify_requests';
const configuredApiUrl = import.meta.env.VITE_API_URL;

const EMPTY_CART = { pedido_id: null, itens: [], subtotal: 0, total: 0 };

const EMPTY_ADDRESS_FIELDS = {
  cep: '',
  endereco: '',
  numero: '',
  complemento: '',
  bairro: '',
  cidade: '',
  estado: '',
};

function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(Number(value || 0));
}

function formatDateTime(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '-';
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(parsed);
}

function resolveProductPrice(product) {
  return Number(
    product?.preco_venda ??
      product?.preco ??
      product?.preco_promocional ??
      0
  );
}

function resolveProductStock(product) {
  const ecommerceStock = Number(product?.estoque_ecommerce);
  const currentStock = Number(product?.estoque_atual);

  if (Number.isFinite(ecommerceStock) && ecommerceStock > 0) {
    return ecommerceStock;
  }

  if (Number.isFinite(currentStock)) {
    return currentStock;
  }

  if (Number.isFinite(ecommerceStock)) {
    return ecommerceStock;
  }

  return Number.POSITIVE_INFINITY;
}

function isProductOutOfStock(product) {
  const stock = resolveProductStock(product);
  return Number.isFinite(stock) && stock <= 0;
}

async function fetchAddressByCep(cep) {
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

function buildIdempotencyKey() {
  if (window?.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function resolveMediaUrl(url) {
  if (!url || typeof url !== 'string') return '';
  if (/^https?:\/\//i.test(url)) return url;

  const normalizedPath = url.startsWith('/') ? url : `/${url}`;
  if (configuredApiUrl && /^https?:\/\//i.test(configuredApiUrl)) {
    const backendBase = configuredApiUrl.replace(/\/api\/?$/, '').replace(/\/$/, '');
    return `${backendBase}${normalizedPath}`;
  }

  if (import.meta.env.DEV) {
    return `http://127.0.0.1:8000${normalizedPath}`;
  }

  return `${window.location.origin}${normalizedPath}`;
}

function normalizeProductPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.itens)) return payload.itens;
  if (Array.isArray(payload?.produtos)) return payload.produtos;
  return [];
}

function getGuestCart() {
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

function recalculateGuestCart(items) {
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

function getStoredAddressFields() {
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

function buildAddressText(fields) {
  const rua = [fields.endereco, fields.numero].filter(Boolean).join(', ');
  const bairro = fields.bairro ? `Bairro: ${fields.bairro}` : '';
  const cidadeUf = [fields.cidade, fields.estado].filter(Boolean).join('/');
  const cep = fields.cep ? `CEP: ${fields.cep}` : '';
  const complemento = fields.complemento ? `Compl.: ${fields.complemento}` : '';

  return [rua, bairro, cidadeUf, cep, complemento].filter(Boolean).join(' | ');
}

function getProductImages(product) {
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

function isLikelyCorruptedText(value) {
  const text = String(value || '');
  if (!text) return false;
  return text.includes('??') || text.includes('�') || /\?{2,}/.test(text);
}

function humanizeSlug(slug) {
  return String(slug || '')
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function extractApiErrorMessage(err, fallback) {
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

const BANNERS = [
  {
    bg: 'linear-gradient(135deg, #f97316 0%, #ea580c 60%, #c2410c 100%)',
    title: 'Compre e receba no mesmo dia!',
    sub: 'Pedidos realizados até as 16h',
    emoji: '🚀',
  },
  {
    bg: 'linear-gradient(135deg, #10b981 0%, #059669 60%, #047857 100%)',
    title: 'Retire na loja',
    sub: 'Super simples e sem custo de frete!',
    emoji: '🏪',
  },
  {
    bg: 'linear-gradient(135deg, #f59e0b 0%, #d97706 60%, #b45309 100%)',
    title: 'As melhores rações em Prudente',
    sub: 'Cachorros, gatos, pássaros e mais 🐾',
    emoji: '🐶',
  },
];

export default function EcommerceMVP() {
  // Inject Plus Jakarta Sans font (matches design system)
  useEffect(() => {
    const id = 'plus-jakarta-sans-font';
    if (!document.getElementById(id)) {
      const link = document.createElement('link');
      link.id = id;
      link.rel = 'stylesheet';
      link.href = 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap';
      document.head.appendChild(link);
    }
  }, []);

  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  const [view, setView] = useState('loja');

  // Rastreia no Google Analytics sempre que o cliente muda de tela
  useEffect(() => {
    trackPageView(view);
    if (view === 'carrinho') trackViewCart(cart);
  }, [view]);
  const [bannerSlide, setBannerSlide] = useState(0);
  const [hoveredCard, setHoveredCard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');
  const [categoria, setCategoria] = useState('todas');
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);
  const [showLoginPassword, setShowLoginPassword] = useState(false);

  const [authLoading, setAuthLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [cartLoading, setCartLoading] = useState(false);

  const [customerToken, setCustomerToken] = useState(localStorage.getItem(STORAGE_TOKEN_KEY) || '');
  const [customer, setCustomer] = useState(null);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileForm, setProfileForm] = useState({
    nome: '',
    telefone: '',
    cpf: '',
    cep: '',
    endereco: '',
    numero: '',
    complemento: '',
    bairro: '',
    cidade: '',
    estado: '',
    endereco_entrega: '',
    usar_endereco_entrega_diferente: false,
    entrega_nome: '',
    entrega_cep: '',
    entrega_endereco: '',
    entrega_numero: '',
    entrega_complemento: '',
    entrega_bairro: '',
    entrega_cidade: '',
    entrega_estado: '',
  });

  const [registerForm, setRegisterForm] = useState({ email: '', password: '', nome: '' });
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });

  const [cart, setCart] = useState(() => getGuestCart());
  const [cupom, setCupom] = useState('');
  const [cupomResult, setCupomResult] = useState(null);

  const [cidadeDestino, setCidadeDestino] = useState('');
  const [deliveryMode, setDeliveryMode] = useState('entrega');
  const [tipoRetirada, setTipoRetirada] = useState('proprio'); // 'proprio' | 'terceiro'
  const [addressFields, setAddressFields] = useState(() => getStoredAddressFields());
  const [checkoutResumo, setCheckoutResumo] = useState(null);
  const [checkoutResult, setCheckoutResult] = useState(null);
  const [pagamentoTipo, setPagamentoTipo] = useState(''); // 'dinheiro'|'pix'|'debito'|'credito'
  const [pagamentoBandeira, setPagamentoBandeira] = useState('Visa');
  const [pagamentoParcelas, setPagamentoParcelas] = useState(1);
  const [pagamentoTroco, setPagamentoTroco] = useState('');
  const [activeProductImage, setActiveProductImage] = useState('');

  const [orderIds, setOrderIds] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_ORDERS_KEY) || '[]');
    } catch {
      return [];
    }
  });
  const [ordersDetailed, setOrdersDetailed] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [wishlist, setWishlist] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_WISHLIST_KEY) || '[]');
    } catch {
      return [];
    }
  });
  const [notifyRequests, setNotifyRequests] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_NOTIFY_KEY) || '[]');
    } catch {
      return [];
    }
  });
  const [notifyMeModal, setNotifyMeModal] = useState({ open: false, product: null, email: '', loading: false });

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [tenantContext, setTenantContext] = useState(null);

  // Banners: usa URLs do tenant se configuradas, senão exibe os padrões
  const activeBanners = useMemo(() => {
    const urls = [
      tenantContext?.banner_1_url,
      tenantContext?.banner_2_url,
      tenantContext?.banner_3_url,
    ].filter(Boolean);
    if (urls.length > 0) return urls.map((url) => ({ type: 'image', url }));
    return BANNERS.map((b) => ({ ...b, type: 'text' }));
  }, [tenantContext?.banner_1_url, tenantContext?.banner_2_url, tenantContext?.banner_3_url]);

  const isProfileComplete = useMemo(() => {
    const fullName = String(customer?.nome || '').trim();
    const hasFullName = fullName.includes(' ');
    const hasPhone = String(customer?.telefone || '').trim().length >= 8;
    const hasCpf = String(customer?.cpf || '').replace(/\D+/g, '').length >= 11;
    const hasAddress = String(customer?.endereco || '').trim().length > 3;
    return hasFullName && hasPhone && hasCpf && hasAddress;
  }, [customer]);

  const tenantRef = useMemo(() => {
    const query = new URLSearchParams(location.search);
    const tenantFromQuery = query.get('tenant');
    return tenantFromQuery || params.tenantId || '';
  }, [location.search, params.tenantId]);

  const tenantHeaders = useMemo(() => {
    if (!tenantContext?.id) return {};
    return { 'X-Tenant-ID': tenantContext.id };
  }, [tenantContext?.id]);

  const authHeaders = useMemo(() => {
    if (!customerToken) return {};
    return { Authorization: `Bearer ${customerToken}` };
  }, [customerToken]);

  const categorias = useMemo(() => {
    const all = products
      .map((item) => item?.categoria_nome || item?.categoria || 'Sem categoria')
      .filter(Boolean);
    return ['todas', ...Array.from(new Set(all))];
  }, [products]);

  const filteredProducts = useMemo(() => {
    const query = search.trim().toLowerCase();
    return products.filter((item) => {
      const nome = String(item?.nome || '').toLowerCase();
      const codigo = String(item?.codigo || '').toLowerCase();
      const categoriaNome = item?.categoria_nome || item?.categoria || 'Sem categoria';
      const matchesSearch = !query || nome.includes(query) || codigo.includes(query);
      const matchesCategoria = categoria === 'todas' || categoriaNome === categoria;
      return matchesSearch && matchesCategoria;
    });
  }, [products, search, categoria]);

  const productMap = useMemo(() => Object.fromEntries(products.map((p) => [p.id, p])), [products]);
  const storefrontRef = tenantContext?.ecommerce_slug || tenantRef || '';
  const customerDisplayName = customer?.nome || customer?.email || '';

  const storeDisplayName = useMemo(() => {
    const backendName = tenantContext?.name || '';
    if (backendName && !isLikelyCorruptedText(backendName)) {
      return backendName;
    }
    if (storefrontRef) {
      return humanizeSlug(storefrontRef);
    }
    return 'Loja online';
  }, [tenantContext?.name, storefrontRef]);

  // Ler ?busca= da URL (ex: link do email de avise-me) e pré-filtrar
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const buscaParam = params.get('busca');
    if (buscaParam) {
      setSearch(buscaParam);
    }
  }, [location.search]);

  useEffect(() => {
    // Sem slug = acesso pelo painel (usuario logado) → carrega via API autenticada
    loadTenantContext();
    if (tenantRef) {
      loadProducts();
    }
  }, [tenantRef]);

  // Apos carregar o contexto via painel (sem slug), usar o tenant.id para buscar produtos
  // e redirecionar para a URL real da loja (/{slug})
  useEffect(() => {
    if (!tenantRef && tenantContext?.id) {
      if (tenantContext.ecommerce_slug) {
        navigate(`/${tenantContext.ecommerce_slug}`, { replace: true });
      } else {
        loadProductsById(tenantContext.id);
      }
    }
  }, [tenantContext?.id]);

  useEffect(() => {
    if (customerToken) {
      loadMe();
      loadCart();
    }
  }, [customerToken]);

  useEffect(() => {
    if (tenantContext?.cidade && !cidadeDestino) {
      setCidadeDestino(tenantContext.cidade);
    }
  }, [tenantContext?.cidade, cidadeDestino]);

  useEffect(() => {
    if (!customerToken) {
      localStorage.setItem(STORAGE_GUEST_CART_KEY, JSON.stringify(cart || EMPTY_CART));
    }
  }, [cart, customerToken]);

  useEffect(() => {
    localStorage.setItem(STORAGE_WISHLIST_KEY, JSON.stringify(wishlist));
  }, [wishlist]);

  useEffect(() => {
    localStorage.setItem(STORAGE_NOTIFY_KEY, JSON.stringify(notifyRequests));
  }, [notifyRequests]);

  useEffect(() => {
    const total = activeBanners.length;
    const timer = setInterval(() => setBannerSlide((prev) => (prev + 1) % total), 4000);
    return () => clearInterval(timer);
  }, [activeBanners.length]);

  useEffect(() => {
    if (!customer) return;
    const deliveryDetails = customer?.endereco_entrega_detalhado || {};
    setProfileForm({
      nome: customer?.nome || '',
      telefone: customer?.telefone || '',
      cpf: customer?.cpf || '',
      cep: customer?.cep || '',
      endereco: customer?.endereco || '',
      numero: customer?.numero || '',
      complemento: customer?.complemento || '',
      bairro: customer?.bairro || '',
      cidade: customer?.cidade || '',
      estado: customer?.estado || '',
      endereco_entrega: customer?.endereco_entrega || '',
      usar_endereco_entrega_diferente: Boolean(customer?.usar_endereco_entrega_diferente),
      entrega_nome: deliveryDetails?.entrega_nome || '',
      entrega_cep: deliveryDetails?.entrega_cep || '',
      entrega_endereco: deliveryDetails?.entrega_endereco || '',
      entrega_numero: deliveryDetails?.entrega_numero || '',
      entrega_complemento: deliveryDetails?.entrega_complemento || '',
      entrega_bairro: deliveryDetails?.entrega_bairro || '',
      entrega_cidade: deliveryDetails?.entrega_cidade || '',
      entrega_estado: deliveryDetails?.entrega_estado || '',
    });
  }, [customer]);

  useEffect(() => {
    if (!customer) return;

    const deliveryDetails = customer?.endereco_entrega_detalhado || {};
    const useDeliveryAddress = Boolean(customer?.usar_endereco_entrega_diferente);

    setAddressFields({
      cep: useDeliveryAddress
        ? (deliveryDetails?.entrega_cep || customer?.cep || '')
        : (customer?.cep || ''),
      endereco: useDeliveryAddress
        ? (deliveryDetails?.entrega_endereco || customer?.endereco || '')
        : (customer?.endereco || ''),
      numero: useDeliveryAddress
        ? (deliveryDetails?.entrega_numero || customer?.numero || '')
        : (customer?.numero || ''),
      complemento: useDeliveryAddress
        ? (deliveryDetails?.entrega_complemento || customer?.complemento || '')
        : (customer?.complemento || ''),
      bairro: useDeliveryAddress
        ? (deliveryDetails?.entrega_bairro || customer?.bairro || '')
        : (customer?.bairro || ''),
      cidade: useDeliveryAddress
        ? (deliveryDetails?.entrega_cidade || customer?.cidade || '')
        : (customer?.cidade || ''),
      estado: useDeliveryAddress
        ? (deliveryDetails?.entrega_estado || customer?.estado || '')
        : (customer?.estado || ''),
    });
  }, [customer]);

  async function loadTenantContext() {
    try {
      // Sem slug na URL = acesso pelo painel (usuario logado) → usa API autenticada
      if (!tenantRef) {
        const response = await api.get('/ecommerce-aparencia/tenant-context');
        setTenantContext(response?.data || null);
        return;
      }
      const response = await ecommerceApi.get('/api/ecommerce/tenant-context', {
        params: { tenant: tenantRef },
      });
      setTenantContext(response?.data || null);
    } catch (err) {
      setTenantContext(null);
      setError(extractApiErrorMessage(err, 'Loja inválida para e-commerce'));
    }
  }

  async function loadProducts() {
    if (!tenantRef) return;
    setLoading(true);
    setError('');
    try {
      const response = await ecommerceApi.get('/api/ecommerce/produtos', {
        params: { tenant: tenantRef, limit: 100, busca: search || undefined },
      });
      setProducts(normalizeProductPayload(response?.data));
    } catch (err) {
      setProducts([]);
      setError(extractApiErrorMessage(err, 'Erro ao carregar produtos vendáveis'));
    } finally {
      setLoading(false);
    }
  }

  async function loadProductsById(tenantId) {
    setLoading(true);
    setError('');
    try {
      const response = await ecommerceApi.get('/api/ecommerce/produtos', {
        params: { tenant: tenantId, limit: 100, busca: search || undefined },
      });
      setProducts(normalizeProductPayload(response?.data));
    } catch (err) {
      setProducts([]);
      setError(extractApiErrorMessage(err, 'Erro ao carregar produtos vendáveis'));
    } finally {
      setLoading(false);
    }
  }

  async function loadMe() {
    if (!customerToken) return;
    try {
      const response = await ecommerceApi.get('/api/ecommerce/auth/perfil', { headers: authHeaders });
      setCustomer(response.data);
    } catch {
      setCustomer(null);
      setCustomerToken('');
      localStorage.removeItem(STORAGE_TOKEN_KEY);
      setCart(getGuestCart());
    }
  }

  async function saveProfile(e) {
    e.preventDefault();
    if (!customerToken) {
      setError('Faça login para atualizar seus dados.');
      return;
    }

    const fullName = String(profileForm.nome || '').trim();
    if (!fullName || !fullName.includes(' ')) {
      setError('Informe nome completo (nome e sobrenome).');
      return;
    }

    if (profileForm.usar_endereco_entrega_diferente) {
      const requiredDelivery = [
        profileForm.entrega_nome,
        profileForm.entrega_endereco,
        profileForm.entrega_numero,
        profileForm.entrega_bairro,
        profileForm.entrega_cidade,
        profileForm.entrega_estado,
      ].every((item) => String(item || '').trim());

      if (!requiredDelivery) {
        setError('Preencha o endereço de entrega completo para continuar.');
        return;
      }
    }

    setProfileSaving(true);
    setError('');
    setSuccess('');
    try {
      const response = await ecommerceApi.put('/api/ecommerce/auth/perfil', profileForm, { headers: authHeaders });
      setCustomer(response.data);
      setSuccess('Dados cadastrais atualizados com sucesso.');
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao salvar dados cadastrais'));
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleProfileCepBlur() {
    const data = await fetchAddressByCep(profileForm.cep);
    if (!data) return;
    setProfileForm((prev) => ({
      ...prev,
      cep: data.cep || prev.cep,
      endereco: data.endereco || prev.endereco,
      bairro: data.bairro || prev.bairro,
      cidade: data.cidade || prev.cidade,
      estado: data.estado || prev.estado,
    }));
  }

  async function handleDeliveryCepBlur() {
    const data = await fetchAddressByCep(profileForm.entrega_cep);
    if (!data) return;
    setProfileForm((prev) => ({
      ...prev,
      entrega_cep: data.cep || prev.entrega_cep,
      entrega_endereco: data.endereco || prev.entrega_endereco,
      entrega_bairro: data.bairro || prev.entrega_bairro,
      entrega_cidade: data.cidade || prev.entrega_cidade,
      entrega_estado: data.estado || prev.entrega_estado,
    }));
  }

  async function handleCheckoutCepBlur() {
    const data = await fetchAddressByCep(addressFields.cep);
    if (!data) return;
    setAddressFields((prev) => ({
      ...prev,
      cep: data.cep || prev.cep,
      endereco: data.endereco || prev.endereco,
      bairro: data.bairro || prev.bairro,
      cidade: data.cidade || prev.cidade,
      estado: data.estado || prev.estado,
    }));
  }

  async function loadCart(customHeaders = authHeaders) {
    if (!customHeaders?.Authorization) return;
    setCartLoading(true);
    try {
      const response = await ecommerceApi.get('/api/carrinho', { headers: customHeaders });
      setCart(response.data || { ...EMPTY_CART });
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao carregar carrinho'));
    } finally {
      setCartLoading(false);
    }
  }

  async function syncGuestCartToServer(token) {
    const guestCart = getGuestCart();
    if (!guestCart?.itens?.length) return;

    const headers = { Authorization: `Bearer ${token}` };

    for (const item of guestCart.itens) {
      await ecommerceApi.post(
        '/api/carrinho/adicionar',
        {
          produto_id: item.produto_id,
          quantidade: item.quantidade,
        },
        { headers }
      );
    }

    await loadCart(headers);
    localStorage.removeItem(STORAGE_GUEST_CART_KEY);
  }

  async function handleRegister(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      setError('Loja não identificada na URL.');
      return;
    }
    setAuthLoading(true);
    setError('');
    setSuccess('');
    try {
      const response = await ecommerceApi.post('/api/ecommerce/auth/registrar', registerForm, { headers: tenantHeaders });
      const token = response?.data?.access_token;
      if (!token) throw new Error('Token não retornado');
      if (response?.data?.user) {
        setCustomer(response.data.user);
      }
      localStorage.setItem(STORAGE_TOKEN_KEY, token);
      setCustomerToken(token);
      await syncGuestCartToServer(token);
      setRegisterForm({ email: '', password: '', nome: '' });
      setSuccess('Cadastro realizado com sucesso. Complete seus dados na aba Conta.');
      setView('conta');
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao cadastrar cliente'));
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      setError('Loja não identificada na URL.');
      return;
    }
    setAuthLoading(true);
    setError('');
    setSuccess('');
    try {
      const response = await ecommerceApi.post('/api/ecommerce/auth/login', loginForm, { headers: tenantHeaders });
      const token = response?.data?.access_token;
      if (!token) throw new Error('Token não retornado');
      if (response?.data?.user) {
        setCustomer(response.data.user);
      }
      localStorage.setItem(STORAGE_TOKEN_KEY, token);
      setCustomerToken(token);
      await syncGuestCartToServer(token);
      setLoginForm({ email: '', password: '' });
      setSuccess('Login realizado com sucesso. Confira seus dados cadastrais.');
      setView('conta');
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao realizar login'));
    } finally {
      setAuthLoading(false);
    }
  }

  function logoutCustomer() {
    setCustomer(null);
    setCustomerToken('');
    setCart({ ...EMPTY_CART });
    setCheckoutResumo(null);
    setCheckoutResult(null);
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    setSuccess('Sessão encerrada.');
  }

  function toggleWishlist(productId) {
    setWishlist((prev) => {
      if (prev.includes(productId)) {
        setSuccess('Produto removido da sua lista de desejos.');
        return prev.filter((id) => id !== productId);
      }
      setSuccess('Produto adicionado à sua lista de desejos.');
      return [...prev, productId];
    });
  }

  function registerNotifyMe(product) {
    const fallbackEmail = customer?.email || registerForm.email || loginForm.email || '';
    setNotifyMeModal({ open: true, product, email: fallbackEmail, loading: false });
  }

  async function submitNotifyMe(e) {
    e.preventDefault();
    const { product, email } = notifyMeModal;
    if (!email.trim() || !product) return;
    setNotifyMeModal((prev) => ({ ...prev, loading: true }));
    const tenantParam = tenantContext?.id || storefrontRef || tenantRef;
    try {
      await ecommerceApi.post('/api/ecommerce-notify/registrar', {
        email: email.trim(),
        product_id: product.id,
        product_name: product.nome,
        tenant_id: tenantParam,
      });
      setNotifyMeModal({ open: false, product: null, email: '', loading: false });
      setSuccess('Perfeito! Te avisaremos por e-mail quando o produto voltar ao estoque. 📧');
      setNotifyRequests((prev) => {
        const exists = prev.some(
          (item) => item.productId === product.id && String(item.email || '').toLowerCase() === email.trim().toLowerCase()
        );
        if (exists) return prev;
        return [...prev, { productId: product.id, productName: product.nome, email: email.trim(), createdAt: new Date().toISOString() }];
      });
    } catch {
      setNotifyMeModal((prev) => ({ ...prev, loading: false }));
      setError('Não foi possível registrar o aviso. Tente novamente.');
    }
  }

  async function addToCart(product) {
    const availableStock = resolveProductStock(product);
    if (availableStock <= 0) {
      setError('Produto indisponível no momento. Volto em breve.');
      return;
    }

    if (!customerToken) {
      setError('');
      const price = resolveProductPrice(product);
      setCart((previousCart) => {
        const currentItems = Array.isArray(previousCart?.itens) ? previousCart.itens : [];
        const existing = currentItems.find((item) => item.produto_id === product.id);

        const nextItems = existing
          ? currentItems.map((item) =>
              item.produto_id === product.id
                ? { ...item, quantidade: Number(item.quantidade || 0) + 1 }
                : item
            )
          : [
              ...currentItems,
              {
                item_id: `guest-${product.id}`,
                produto_id: product.id,
                nome: product.nome,
                preco_unitario: price,
                quantidade: 1,
              },
            ];

        return recalculateGuestCart(nextItems);
      });
      setSuccess('Produto adicionado ao carrinho. Faça login no checkout para finalizar.');
      trackAddToCart(product);
      return;
    }

    setError('');
    try {
      const response = await ecommerceApi.post(
        '/api/carrinho/adicionar',
        { produto_id: product.id, quantidade: 1 },
        { headers: authHeaders }
      );
      setCart(response.data);
      setSuccess('Produto adicionado ao carrinho.');
      trackAddToCart(product);
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao adicionar no carrinho'));
    }
  }

  async function updateCartItem(itemId, quantidade) {
    if (!customerToken) {
      setCart((previousCart) => {
        const currentItems = Array.isArray(previousCart?.itens) ? previousCart.itens : [];

        if (quantidade <= 0) {
          const nextItems = currentItems.filter((item) => item.item_id !== itemId);
          return recalculateGuestCart(nextItems);
        }

        const nextItems = currentItems.map((item) =>
          item.item_id === itemId ? { ...item, quantidade } : item
        );
        return recalculateGuestCart(nextItems);
      });
      return;
    }
    setError('');
    try {
      if (quantidade <= 0) {
        const response = await ecommerceApi.delete(`/api/carrinho/remover/${itemId}`, { headers: authHeaders });
        setCart(response.data);
        return;
      }
      const response = await ecommerceApi.put(
        `/api/carrinho/atualizar/${itemId}`,
        { quantidade },
        { headers: authHeaders }
      );
      setCart(response.data);
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao atualizar carrinho'));
    }
  }

  async function applyCupom(e) {
    e.preventDefault();
    if (!customerToken) {
      setError('Faça login para aplicar cupom.');
      setView('conta');
      return;
    }
    if (!cupom.trim()) return;
    setError('');
    try {
      const response = await ecommerceApi.post(
        '/api/carrinho/aplicar-cupom',
        { codigo: cupom.trim() },
        { headers: authHeaders }
      );
      setCupomResult(response.data);
      setSuccess('Cupom validado.');
    } catch (err) {
      setCupomResult(null);
      setError(extractApiErrorMessage(err, 'Cupom inválido'));
    }
  }

  async function calcularResumoCheckout(e) {
    e.preventDefault();
    if (!customerToken) {
      setError('Faça login para continuar no checkout.');
      setView('conta');
      return;
    }
    if (!cart?.itens?.length) {
      setError('Adicione itens no carrinho antes de calcular o checkout.');
      return;
    }

    const cidadeFinal = (tenantContext?.cidade || cidadeDestino || addressFields.cidade || '').trim();
    if (!cidadeFinal || cidadeFinal.length < 2) {
      setError('Cidade da loja não configurada para checkout.');
      return;
    }

    setError('');
    setCheckoutResumo(null);
    try {
      const response = await ecommerceApi.get('/api/checkout/resumo', {
        headers: authHeaders,
        params: {
          cidade_destino: cidadeFinal,
          cupom: cupomResult?.codigo || undefined,
        },
      });
      setCheckoutResumo(response.data);
      setSuccess('Resumo de checkout calculado.');
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao calcular resumo do checkout'));
    }
  }



  async function finalizarCheckout() {
    if (!customerToken) {
      setError('Faça login para finalizar o pedido.');
      setView('conta');
      return;
    }
    if (!isProfileComplete) {
      setError('Complete seu cadastro antes de finalizar o pedido.');
      setView('conta');
      return;
    }
    const cidadeFinal = (tenantContext?.cidade || cidadeDestino || addressFields.cidade || '').trim();
    if (!cidadeFinal || cidadeFinal.length < 2) {
      setError('Cidade da loja não configurada para checkout.');
      return;
    }

    const enderecoFormatado =
      deliveryMode === 'retirada'
        ? 'RETIRADA NA LOJA'
        : buildAddressText(addressFields);

    if (deliveryMode === 'entrega' && !enderecoFormatado) {
      setError('Informe o endereço de entrega.');
      return;
    }

    setCheckoutLoading(true);
    setError('');
    setSuccess('');
    setCheckoutResult(null);

    try {
      const response = await ecommerceApi.post(
        '/api/checkout/finalizar',
        {
          cidade_destino: cidadeFinal,
          endereco_entrega: enderecoFormatado || null,
          cupom: cupomResult?.codigo || null,
          tipo_retirada: deliveryMode === 'retirada' ? tipoRetirada : null,
          forma_pagamento_nome: (() => {
            if (pagamentoTipo === 'dinheiro') return pagamentoTroco ? `Dinheiro (troco p/ R$ ${pagamentoTroco})` : 'Dinheiro';
            if (pagamentoTipo === 'pix') return 'PIX';
            if (pagamentoTipo === 'debito') return `Débito ${pagamentoBandeira}`;
            if (pagamentoTipo === 'credito') return `Crédito ${pagamentoBandeira} ${pagamentoParcelas}x`;
            return null;
          })(),
        },
        {
          headers: {
            ...authHeaders,
            'Idempotency-Key': buildIdempotencyKey(),
          },
        }
      );

      const result = response.data;
      setCheckoutResult(result);
      trackPurchase(result, cart);
      setCart({ pedido_id: null, itens: [], subtotal: 0, total: 0 });
      setCheckoutResumo(null);
      setCupomResult(null);
      setCupom('');
      if (deliveryMode === 'entrega') {
        localStorage.setItem(STORAGE_ADDRESS_KEY, JSON.stringify(addressFields));
      }

      if (result?.pedido_id) {
        const updated = Array.from(new Set([result.pedido_id, ...orderIds]));
        setOrderIds(updated);
        localStorage.setItem(STORAGE_ORDERS_KEY, JSON.stringify(updated));
        await loadOrdersDetailed();
      }

      setSuccess('Pedido finalizado com sucesso.');
      setView('pedidos');
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao finalizar checkout'));
    } finally {
      setCheckoutLoading(false);
    }
  }

  async function loadOrdersDetailed() {
    if (!customerToken) return;
    setOrdersLoading(true);
    try {
      const response = await ecommerceApi.get('/api/checkout/pedidos', {
        headers: authHeaders,
        params: { limit: 20 },
      });
      const pedidos = Array.isArray(response?.data?.pedidos) ? response.data.pedidos : [];
      setOrdersDetailed(pedidos);

      if (pedidos.length) {
        const ids = pedidos.map((pedido) => pedido?.pedido_id).filter(Boolean);
        const updated = Array.from(new Set([...ids, ...orderIds]));
        setOrderIds(updated);
        localStorage.setItem(STORAGE_ORDERS_KEY, JSON.stringify(updated));
      }
    } catch (err) {
      setOrdersDetailed([]);
      setError(extractApiErrorMessage(err, 'Erro ao carregar detalhes dos pedidos'));
    } finally {
      setOrdersLoading(false);
    }
  }

  useEffect(() => {
    if (!customerToken || view !== 'pedidos') return;
    loadOrdersDetailed();
  }, [view, customerToken]);

  const cartTotal = Number(cart?.total || 0);

  function handleCheckoutFromLoja() {
    if (!cart?.itens?.length) {
      setError('Adicione itens no carrinho antes de finalizar.');
      return;
    }
    if (!customerToken) {
      setError('Faça login para finalizar o pedido.');
      setView('conta');
      return;
    }
    if (!isProfileComplete) {
      setError('Complete seu cadastro (nome completo, telefone, CPF e endereço) antes de finalizar.');
      setView('conta');
      return;
    }
    setView('checkout');
    trackBeginCheckout(cart);
  }

  function openProductDetails(product) {
    const images = getProductImages(product);
    setSelectedProduct(product);
    setActiveProductImage(images[0] || '');
    navigate(`${location.pathname}?produto=${product.id}`, { replace: true });
    trackViewItem(product);
  }

  function closeProductModal() {
    setSelectedProduct(null);
    navigate(location.pathname, { replace: true });
  }

  // Fecha o modal com ESC
  useEffect(() => {
    if (!selectedProduct) return;
    function handleKeyDown(e) {
      if (e.key === 'Escape') closeProductModal();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedProduct]);

  // Abre produto automaticamente pelo link direto (?produto=ID)
  useEffect(() => {
    if (!products.length) return;
    const searchParams = new URLSearchParams(location.search);
    const prodIdFromUrl = searchParams.get('produto');
    if (!prodIdFromUrl || selectedProduct) return;
    const found = products.find((p) => String(p.id) === String(prodIdFromUrl));
    if (found) openProductDetails(found);
  }, [products.length, location.search]);

  /* ─────────────── ESTILOS INTERNOS ─────────────── */
  const S = {
    page: { minHeight: '100vh', background: '#faf7f4', fontFamily: "'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif" },
    /* Topbar */
    topbar: { background: 'linear-gradient(90deg,#f97316 0%,#fb923c 100%)', color: '#fff', padding: '8px 20px', fontSize: 13, fontWeight: 500 },
    topbarInner: { maxWidth: 1280, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
    header: { background: '#fff', borderBottom: '1px solid #e7e5e4', padding: '12px 20px', position: 'sticky', top: 0, zIndex: 40, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
    headerInner: { maxWidth: 1280, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 },
    logo: { fontSize: 20, fontWeight: 800, color: '#1c1917', display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' },
    cityChip: { fontSize: 11, color: '#a8a29e', borderLeft: '1px solid #e7e5e4', paddingLeft: 12, fontWeight: 400 },
    headerActions: { display: 'flex', gap: 10, alignItems: 'center' },
    avatarBtn: { background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 24, padding: '7px 14px', fontSize: 13, fontWeight: 600, color: '#ea580c', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' },
    loginBtn: { background: '#fff', border: '1.5px solid #d1d5db', color: '#374151', borderRadius: 24, padding: '7px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 },
    cartBtn: { background: '#f97316', color: '#fff', border: 'none', borderRadius: 12, width: 42, height: 42, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', flexShrink: 0 },
    cartBadge: { position: 'absolute', top: -5, right: -5, background: '#10b981', color: '#fff', borderRadius: 20, minWidth: 18, height: 18, fontSize: 10, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #fff', padding: '0 3px' },
    /* Floating cart bar */
    floatBar: { position: 'sticky', top: 0, zIndex: 45, background: '#ea580c', color: '#fff', padding: '10px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' },
    /* Nav tabs */
    navWrap: { background: '#fff', borderBottom: '1px solid #e7e5e4' },
    navInner: { maxWidth: 1280, margin: '0 auto', display: 'flex', padding: '0 20px' },
    navTab: (active) => ({ flex: '0 0 auto', background: 'transparent', border: 'none', borderBottom: active ? '2px solid #f97316' : '2px solid transparent', color: active ? '#f97316' : '#78716c', padding: '13px 18px', fontWeight: active ? 700 : 500, fontSize: 14, cursor: 'pointer', transition: 'all 0.15s', marginBottom: -1 }),
    /* Banner */
    bannerWrap: { position: 'relative', overflow: 'hidden', height: 320, background: '#1c1917' },
    bannerDots: { position: 'absolute', bottom: 14, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 6 },
    bannerDot: (active) => ({ width: active ? 26 : 9, height: 9, background: active ? '#fff' : 'rgba(255,255,255,0.4)', borderRadius: 5, border: 'none', cursor: 'pointer', padding: 0, transition: 'all 0.3s' }),
    /* Alert messages */
    alertError: { background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca', borderRadius: 10, padding: '10px 14px', fontSize: 13, margin: '12px 20px' },
    alertSuccess: { background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0', borderRadius: 10, padding: '10px 14px', fontSize: 13, margin: '12px 20px' },
    /* Main layout */
    main: { maxWidth: 1280, margin: '0 auto', padding: '24px 20px' },
    /* Product grid */
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 },
    /* Card */
    card: (hovered) => ({ border: '1px solid #e7e5e4', borderRadius: 14, background: '#fff', cursor: 'pointer', display: 'flex', flexDirection: 'column', overflow: 'hidden', transition: 'all 0.2s', boxShadow: hovered ? '0 10px 32px rgba(249,115,22,0.15)' : '0 1px 4px rgba(0,0,0,0.05)', transform: hovered ? 'translateY(-5px)' : 'none' }),
    cardImgWrap: { aspectRatio: '1/1', background: '#f5f5f4', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' },
    cardBody: { padding: '12px 14px 14px', display: 'flex', flexDirection: 'column', gap: 4, flex: 1 },
    cardName: { fontSize: 13, fontWeight: 600, lineHeight: 1.4, color: '#1c1917', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' },
    cardCat: { fontSize: 11, color: '#a8a29e', fontWeight: 500 },
    cardSku: { fontSize: 10, color: '#d6d3d1', letterSpacing: 0.3 },
    cardStock: (out) => ({ fontSize: 11, fontWeight: 600, color: out ? '#d97706' : '#059669' }),
    cardPrice: { fontSize: 19, fontWeight: 800, color: '#1c1917', letterSpacing: -0.5, marginTop: 'auto', paddingTop: 6 },
    addBtn: (out) => ({ background: out ? '#f5f5f4' : 'linear-gradient(135deg,#f97316,#fb923c)', border: 'none', color: out ? '#a8a29e' : '#fff', borderRadius: 9, padding: '10px 0', fontWeight: 700, fontSize: 13, cursor: out ? 'not-allowed' : 'pointer', width: '100%', marginTop: 6, transition: 'opacity 0.15s', boxShadow: out ? 'none' : '0 2px 8px rgba(249,115,22,0.3)' }),
    notifyBtn: { background: '#fff', border: '1.5px solid #f59e0b', color: '#b45309', borderRadius: 9, padding: '8px 0', fontWeight: 600, fontSize: 12, cursor: 'pointer', width: '100%', marginTop: 6 },
    wishBtn: { position: 'absolute', top: 8, right: 8, background: '#fff', border: 'none', borderRadius: '50%', width: 30, height: 30, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', boxShadow: '0 1px 4px rgba(0,0,0,0.12)', fontSize: 14 },
    unavailBadge: { position: 'absolute', top: 8, left: 8, background: '#fee2e2', color: '#991b1b', borderRadius: 6, padding: '3px 8px', fontSize: 10, fontWeight: 700 },
    /* Sidebar */
    sidebar: { background: '#fff', borderRadius: 16, border: '1px solid #e7e5e4', padding: 20, alignSelf: 'start', position: 'sticky', top: 80, boxShadow: '0 2px 12px rgba(0,0,0,0.06)' },
    sidebarTitle: { margin: '0 0 14px', fontSize: 15, fontWeight: 700, color: '#1c1917', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
    sidebarBadge: { background: '#f97316', color: '#fff', borderRadius: 20, padding: '2px 9px', fontSize: 11, fontWeight: 700 },
    miniItem: { display: 'flex', gap: 8, alignItems: 'center', borderBottom: '1px solid #f5f5f4', paddingBottom: 8, marginBottom: 4 },
    miniImg: { width: 42, height: 42, borderRadius: 8, background: '#f5f5f4', flexShrink: 0, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e7e5e4' },
    subtotalBox: { background: '#fff7ed', borderRadius: 10, padding: '10px 12px', marginTop: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid #fed7aa' },
    checkoutBig: { background: 'linear-gradient(135deg,#f97316,#fb923c)', border: 'none', color: '#fff', borderRadius: 10, padding: '12px 0', fontWeight: 700, fontSize: 14, cursor: 'pointer', width: '100%', marginTop: 8, boxShadow: '0 4px 14px rgba(249,115,22,0.35)' },
    viewCartBtn: { background: 'transparent', border: '2px solid #f97316', color: '#f97316', borderRadius: 10, padding: '10px 0', fontWeight: 700, fontSize: 13, cursor: 'pointer', width: '100%', marginTop: 6 },
    /* Cart page */
    cartItem: { border: '1px solid #e7e5e4', borderRadius: 14, padding: '14px', display: 'flex', gap: 14, alignItems: 'center', background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' },
    cartItemImg: { width: 80, height: 80, borderRadius: 10, background: '#f5f5f4', flexShrink: 0, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e7e5e4' },
    qtyBtn: { background: '#f5f5f4', border: '1px solid #d1d5db', borderRadius: 7, width: 32, height: 32, cursor: 'pointer', fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' },
    removeBtn: { background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 12, padding: '4px 8px' },
    cartTotalRow: { border: '1px solid #e7e5e4', borderRadius: 12, padding: '14px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fff' },
    /* Checkout form */
    formCard: { background: '#fff', borderRadius: 14, border: '1px solid #e7e5e4', padding: '20px 24px', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' },
    formLabel: { fontSize: 12, fontWeight: 600, color: '#78716c', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4, display: 'block' },
    formInput: { width: '100%', padding: '10px 12px', border: '1.5px solid #e7e5e4', borderRadius: 9, fontSize: 14, background: '#faf7f4', outline: 'none', boxSizing: 'border-box', transition: 'border-color 0.15s' },
    radioLabel: { display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14, padding: '10px 14px', borderRadius: 10, border: '1.5px solid #e7e5e4', background: '#faf7f4', fontWeight: 500 },
    radioLabelActive: { display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14, padding: '10px 14px', borderRadius: 10, border: '1.5px solid #f97316', background: '#fff7ed', fontWeight: 600, color: '#ea580c' },
    payBtn: (active) => ({ padding: '10px 16px', borderRadius: 10, border: active ? '2px solid #f97316' : '2px solid #e7e5e4', background: active ? '#fff7ed' : '#fff', color: active ? '#ea580c' : '#374151', fontWeight: active ? 700 : 500, cursor: 'pointer', fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }),
    resumoBox: { background: '#fff', border: '1px solid #e7e5e4', borderRadius: 12, padding: '14px 16px', display: 'grid', gap: 6, boxShadow: '0 2px 8px rgba(0,0,0,0.05)' },
    finalizarBtn: (disabled) => ({ background: disabled ? '#e5e7eb' : 'linear-gradient(135deg,#f97316,#fb923c)', border: 'none', color: disabled ? '#9ca3af' : '#fff', borderRadius: 12, padding: '14px 0', fontWeight: 700, fontSize: 16, cursor: disabled ? 'not-allowed' : 'pointer', width: '100%', boxShadow: disabled ? 'none' : '0 4px 14px rgba(249,115,22,0.35)' }),
    /* Orders */
    orderCard: { border: '1px solid #e7e5e4', borderRadius: 14, padding: '16px 20px', background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', display: 'grid', gap: 10 },
    statusBadge: (status) => {
      const map = { confirmado: { bg: '#dcfce7', color: '#166534' }, pendente: { bg: '#fef9c3', color: '#854d0e' }, cancelado: { bg: '#fee2e2', color: '#991b1b' } };
      const s = map[String(status).toLowerCase()] || { bg: '#f5f5f4', color: '#555' };
      return { background: s.bg, color: s.color, borderRadius: 20, padding: '3px 10px', fontSize: 11, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4 };
    },
    rewardBox: { background: '#fff7ed', border: '2px solid #f97316', borderRadius: 10, padding: 12, textAlign: 'center' },
    /* Account */
    accountCard: { background: '#fff', borderRadius: 14, border: '1px solid #e7e5e4', padding: '20px 24px', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' },
    saveBtn: { background: 'linear-gradient(135deg,#f97316,#fb923c)', border: 'none', color: '#fff', borderRadius: 10, fontWeight: 700, padding: '11px 24px', cursor: 'pointer', fontSize: 14 },
    /* Footer */
    footer: { background: '#1c1917', color: '#a8a29e', padding: '32px 20px', marginTop: 40 },
  };

  return (
    <div style={S.page}>
      {/* TOPBAR */}
      <div style={S.topbar}>
        <div style={S.topbarInner}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
            <span style={{ fontWeight: 600 }}>{cart?.itens?.length > 0 ? `${cart.itens.length} item(ns) no carrinho` : 'Carrinho vazio'}</span>
          </div>
          <span style={{ fontWeight: 600 }}>{cart?.itens?.length > 0 ? `${formatCurrency(cartTotal)} →` : 'Frete grátis acima de R$ 199'}</span>
        </div>
      </div>

      {/* HEADER */}
      <div style={S.header}>
        <div style={S.headerInner}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            {tenantContext?.logo_url ? (
              <img src={resolveMediaUrl(tenantContext.logo_url)} alt={storeDisplayName} style={{ height: 44, maxWidth: 160, objectFit: 'contain' }} />
            ) : (
              <div style={S.logo} onClick={() => setView('loja')}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 18.5C8 19.9 7 21 5.5 21S3 19.9 3 18.5 4 16 5.5 16 8 17.1 8 18.5z"/><path d="M21 16.5c0 1.4-1 2.5-2.5 2.5S16 17.9 16 16.5 17 14 18.5 14 21 15.1 21 16.5z"/><path d="M5.5 7C5.5 5.6 6.5 4.5 8 4.5S10.5 5.6 10.5 7 9.5 9.5 8 9.5 5.5 8.4 5.5 7z"/><path d="M13.5 7c0-1.4 1-2.5 2.5-2.5S18.5 5.6 18.5 7 17.5 9.5 16 9.5 13.5 8.4 13.5 7z"/><path d="M12 20c-4 0-6-3-6-6 0-2.5 2-5 6-5s6 2.5 6 5c0 3-2 6-6 6z"/></svg>
                {storeDisplayName}
              </div>
            )}
            {(tenantContext?.cidade || tenantContext?.uf) && (
              <span style={S.cityChip}>
                📍 {tenantContext?.cidade || ''}{tenantContext?.uf ? ` - ${tenantContext.uf}` : ''}
              </span>
            )}
          </div>

          {/* Search (desktop) */}
          <div style={{ flex: 1, maxWidth: 440, display: 'flex' }} className="eco-search-wrap">
            <div style={{ position: 'relative', width: '100%' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar produtos para o seu pet..."
                style={{ ...S.formInput, paddingLeft: 36, borderRadius: 24, fontSize: 13 }}
              />
            </div>
          </div>

          {/* Actions */}
          <div style={S.headerActions}>
            {customerDisplayName ? (
              <button onClick={() => setView('conta')} style={S.avatarBtn}>
                <span style={{ width: 22, height: 22, borderRadius: '50%', background: '#f97316', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800 }}>{customerDisplayName.charAt(0).toUpperCase()}</span>
                {customerDisplayName.split(' ')[0]}
              </button>
            ) : (
              <button onClick={() => setView('conta')} style={S.loginBtn}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                Entrar
              </button>
            )}
            <button onClick={() => setView('carrinho')} style={S.cartBtn}>
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
              {cart?.itens?.length > 0 && (
                <span style={S.cartBadge}>{cart.itens.length}</span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* NAV TABS */}
      <div style={S.navWrap}>
        <div style={S.navInner}>
          {[
            ['loja', '🏪 Loja'],
            ['carrinho', `🛒 Carrinho${cart?.itens?.length ? ` (${cart.itens.length})` : ''}`],
            ['pedidos', '📦 Pedidos'],
            ['conta', '👤 Conta'],
          ].map(([tabId, label]) => (
            <button key={tabId} onClick={() => setView(tabId)} style={S.navTab(view === tabId)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* BARRA FLUTUANTE CARRINHO */}
      {cart?.itens?.length > 0 && view !== 'carrinho' && (
        <div onClick={() => setView('carrinho')} style={S.floatBar}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>🛒 {cart.itens.length} item(ns) no carrinho</span>
          <span style={{ fontWeight: 800, fontSize: 13 }}>{formatCurrency(cartTotal)} → Ver carrinho</span>
        </div>
      )}

      {!tenantRef && (
        <div style={{ background: '#fef2f2', color: '#991b1b', padding: '10px 20px', fontSize: 13, borderBottom: '1px solid #fecaca' }}>
          ⚠️ Use a URL no formato: /slug-da-loja
        </div>
      )}

      {/* ALERTAS */}
      {error && <div style={S.alertError}>⚠️ {error}</div>}
      {success && <div style={S.alertSuccess}>✓ {success}</div>}

      {/* BANNER (só na aba loja) */}
      {view === 'loja' && (
        <div style={S.bannerWrap}>
          {activeBanners.map((b, i) => (
            <div key={i} style={{ position: 'absolute', inset: 0, opacity: bannerSlide === i ? 1 : 0, transition: 'opacity 0.8s ease', pointerEvents: bannerSlide === i ? 'auto' : 'none' }}>
              {b.type === 'image' ? (
                <img src={resolveMediaUrl(b.url)} alt={`Banner ${i + 1}`} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              ) : (
                <div style={{ background: b.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 48px', gap: 24, height: '100%' }}>
                  <span style={{ fontSize: 72, flexShrink: 0, filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.25))' }}>{b.emoji}</span>
                  <div>
                    <div style={{ color: '#fff', fontWeight: 800, fontSize: 34, lineHeight: 1.2, textShadow: '0 2px 12px rgba(0,0,0,0.2)' }}>{b.title}</div>
                    <div style={{ color: 'rgba(255,255,255,0.88)', fontSize: 16, marginTop: 8 }}>{b.sub}</div>
                    <button onClick={() => setView('loja')} style={{ marginTop: 16, background: '#fff', color: '#f97316', border: 'none', borderRadius: 24, padding: '10px 24px', fontWeight: 700, fontSize: 14, cursor: 'pointer' }}>
                      Ver produtos →
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
          <div style={S.bannerDots}>
            {activeBanners.map((_, i) => (
              <button key={i} onClick={() => setBannerSlide(i)} style={S.bannerDot(bannerSlide === i)} />
            ))}
          </div>
        </div>
      )}

      {view === 'loja' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 300px', gap: 24, maxWidth: 1280, margin: '0 auto', padding: '28px 20px' }}>
          {/* PRODUTOS */}
          <div>
            {/* Cabeçalho catalogo */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#1c1917' }}>Catálogo da loja</h2>
                <p style={{ margin: '4px 0 0', color: '#9ca3af', fontSize: 13 }}>{filteredProducts.length} produto{filteredProducts.length !== 1 ? 's' : ''} encontrado{filteredProducts.length !== 1 ? 's' : ''}</p>
              </div>
            </div>

            {/* Buscas e filtro */}
            <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 220, position: 'relative' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="O que seu pet precisa?"
                  style={{ ...S.formInput, paddingLeft: 36 }}
                />
              </div>
              <select value={categoria} onChange={(e) => setCategoria(e.target.value)} style={{ ...S.formInput, width: 'auto', paddingRight: 30 }}>
                {categorias.map((item) => (
                  <option key={item} value={item}>{item === 'todas' ? '🐾 Todas as categorias' : item}</option>
                ))}
              </select>
              <button onClick={loadProducts} disabled={loading} style={{ padding: '10px 16px', border: '1.5px solid #e7e5e4', borderRadius: 9, fontSize: 13, fontWeight: 600, background: '#fff', color: '#f97316', cursor: 'pointer' }}>
                {loading ? '...' : '↺ Atualizar'}
              </button>
            </div>

            {/* Chips de categorias */}
            {categorias.length > 2 && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
                {categorias.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setCategoria(cat)}
                    style={{ padding: '6px 14px', borderRadius: 20, border: categoria === cat ? '1.5px solid #f97316' : '1.5px solid #e7e5e4', background: categoria === cat ? '#fff7ed' : '#fff', color: categoria === cat ? '#ea580c' : '#78716c', fontWeight: categoria === cat ? 700 : 500, fontSize: 12, cursor: 'pointer', transition: 'all 0.15s' }}
                  >
                    {cat === 'todas' ? '🐾 Todas' : cat}
                  </button>
                ))}
              </div>
            )}

            {/* Grid */}
            <div style={S.grid}>
              {filteredProducts.map((product) => {
                const stock = resolveProductStock(product);
                const outOfStock = isProductOutOfStock(product);
                const wished = wishlist.includes(product.id);
                const productImage = getProductImages(product)[0];
                const isHovered = hoveredCard === product.id;

                return (
                  <div
                    role="button"
                    tabIndex={0}
                    key={product.id}
                    onClick={() => openProductDetails(product)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openProductDetails(product); } }}
                    onMouseEnter={() => setHoveredCard(product.id)}
                    onMouseLeave={() => setHoveredCard(null)}
                    style={S.card(isHovered)}
                  >
                    {/* Imagem */}
                    <div style={S.cardImgWrap}>
                      {productImage ? (
                        <img src={productImage} alt={product.nome} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 12, background: '#fff' }} />
                      ) : (
                        <div style={{ color: '#d1d5db', fontSize: 12, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                          <span>Sem imagem</span>
                        </div>
                      )}
                      {outOfStock && <div style={S.unavailBadge}>Indisponível</div>}
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleWishlist(product.id); }}
                        title={wished ? 'Remover da lista de desejos' : 'Adicionar à lista de desejos'}
                        style={S.wishBtn}
                      >{wished ? '❤️' : '🤍'}</button>
                    </div>

                    {/* Info */}
                    <div style={S.cardBody}>
                      <div style={S.cardName}>{product.nome}</div>
                      <div style={S.cardCat}>{product?.categoria_nome || product?.categoria || 'Sem categoria'}</div>
                      <div style={S.cardSku}>SKU: {product?.codigo || '-'}</div>
                      <div style={S.cardStock(outOfStock)}>
                        {outOfStock ? '⚠️ Volto em breve' : Number.isFinite(stock) ? `✓ Em estoque: ${stock}` : '✓ Em estoque'}
                      </div>
                      <div style={S.cardPrice}>{formatCurrency(resolveProductPrice(product))}</div>

                      <button
                        disabled={outOfStock}
                        style={S.addBtn(outOfStock)}
                        onClick={(e) => { e.stopPropagation(); addToCart(product); }}
                      >
                        {outOfStock ? 'Indisponível' : '🛒 Adicionar'}
                      </button>
                      {outOfStock && (
                        <button onClick={(e) => { e.stopPropagation(); registerNotifyMe(product); }} style={S.notifyBtn}>
                          🔔 Avise-me quando chegar
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
              {!loading && filteredProducts.length === 0 && (
                <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '60px 0', color: '#9ca3af' }}>
                  <div style={{ fontSize: 48, marginBottom: 12 }}>🔍</div>
                  <div style={{ fontWeight: 800, fontSize: 18, color: '#374151' }}>Nenhum produto encontrado</div>
                  <div style={{ fontSize: 13, marginTop: 4 }}>Tente buscar por outro termo ou categoria</div>
                  <button onClick={() => { setSearch(''); setCategoria('todas'); }} style={{ marginTop: 16, padding: '8px 20px', borderRadius: 20, border: '1.5px solid #e7e5e4', background: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600, color: '#f97316' }}>
                    Limpar filtros
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* SIDEBAR CARRINHO */}
          <aside style={S.sidebar}>
            <div style={S.sidebarTitle}>
              <span>🛒 Seu carrinho</span>
              {cart?.itens?.length > 0 && <span style={S.sidebarBadge}>{cart.itens.length}</span>}
            </div>
            {cart?.itens?.length ? (
              <div style={{ display: 'grid', gap: 8 }}>
                {cart.itens.slice(0, 5).map((item) => {
                  const prod = productMap[item.produto_id];
                  const img = prod ? getProductImages(prod)[0] : null;
                  return (
                    <div key={item.item_id} style={S.miniItem}>
                      <div style={S.miniImg}>
                        {img ? <img src={img} alt={item.nome} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 2 }} /> : <span style={{ fontSize: 16 }}>📦</span>}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1a1a2e' }}>{item.nome}</div>
                        <div style={{ fontSize: 11, color: '#f97316', fontWeight: 600 }}>{item.quantidade}× {formatCurrency(item.preco_unitario)}</div>
                      </div>
                    </div>
                  );
                })}
                {cart.itens.length > 5 && (
                  <div style={{ fontSize: 12, color: '#9ca3af', textAlign: 'center' }}>+ {cart.itens.length - 5} item(ns) a mais</div>
                )}
                <div style={S.subtotalBox}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#374151' }}>Subtotal</span>
                  <span style={{ fontWeight: 800, fontSize: 17, color: '#1a1a2e' }}>{formatCurrency(cartTotal)}</span>
                </div>
                <button style={S.checkoutBig} onClick={handleCheckoutFromLoja}>
                  Finalizar compra →
                </button>
                <button style={S.viewCartBtn} onClick={() => setView('carrinho')}>Ver / Editar carrinho</button>
                {!customerToken && (
                  <div style={{ fontSize: 11, color: '#9ca3af', textAlign: 'center' }}>🔒 Login solicitado apenas no fechamento</div>
                )}
              </div>
            ) : (
              <div style={{ color: '#c4c4d4', textAlign: 'center', padding: '28px 0', fontSize: 13 }}>
                <div style={{ fontSize: 34, marginBottom: 8 }}>🛒</div>
                <div style={{ fontWeight: 600, color: '#9ca3af' }}>Carrinho vazio</div>
                <div style={{ fontSize: 12, marginTop: 4 }}>Adicione produtos para começar</div>
              </div>
            )}
          </aside>
        </div>
      )}

      {selectedProduct && (
        <div
          role="dialog"
          aria-modal="true"
          style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, zIndex: 60 }}
          onClick={() => closeProductModal()}
        >
          <div
            style={{ background: '#fff', width: 'min(960px, 100%)', maxHeight: '90vh', overflowY: 'auto', borderRadius: 18, border: '1px solid #e5e7eb', boxShadow: '0 24px 80px rgba(0,0,0,0.2)', display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Galeria */}
            <div style={{ background: '#f5f5f4', borderRadius: '18px 0 0 18px', padding: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ borderRadius: 12, background: '#fff', aspectRatio: '1/1', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e7e5e4' }}>
                {activeProductImage ? (
                  <img src={activeProductImage} alt={selectedProduct.nome} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                ) : (
                  <span style={{ color: '#9ca3af', fontSize: 13 }}>Sem imagem disponível</span>
                )}
              </div>
              {getProductImages(selectedProduct).length > 1 && (
                <div style={{ display: 'flex', gap: 8, overflowX: 'auto' }}>
                  {getProductImages(selectedProduct).map((img) => (
                    <button key={img} onClick={() => setActiveProductImage(img)} style={{ border: activeProductImage === img ? '2.5px solid #f97316' : '1.5px solid #e7e5e4', borderRadius: 10, width: 70, height: 70, overflow: 'hidden', padding: 0, background: '#fff', cursor: 'pointer', flexShrink: 0 }}>
                      <img src={img} alt="Miniatura" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Detalhes */}
            <div style={{ padding: 28, display: 'grid', alignContent: 'start', gap: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                <h3 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#1c1917', lineHeight: 1.3 }}>{selectedProduct.nome}</h3>
                <button onClick={() => closeProductModal()} style={{ background: '#f1f5f9', border: 'none', borderRadius: 8, width: 34, height: 34, cursor: 'pointer', fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: '#6b7280' }}>✕</button>
              </div>

              <div style={{ fontSize: 30, fontWeight: 800, color: '#1a1a2e', letterSpacing: -1 }}>
                {formatCurrency(resolveProductPrice(selectedProduct))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, background: '#faf7f4', borderRadius: 10, padding: '12px 14px' }}>
                <div style={{ fontSize: 13, color: '#6b7280' }}>Categoria: <strong style={{ color: '#1a1a2e' }}>{selectedProduct?.categoria_nome || selectedProduct?.categoria || 'Sem categoria'}</strong></div>
                <div style={{ fontSize: 13, color: '#6b7280' }}>SKU: <strong style={{ color: '#1a1a2e', fontFamily: 'monospace' }}>{selectedProduct?.codigo || '-'}</strong></div>
                <div style={{ fontSize: 13, color: isProductOutOfStock(selectedProduct) ? '#b45309' : '#065f46' }}>
                  {isProductOutOfStock(selectedProduct) ? '⚠️ Fora de estoque' : `✓ Em estoque: ${Number.isFinite(resolveProductStock(selectedProduct)) ? resolveProductStock(selectedProduct) : 'Disponível'}`}
                </div>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
                {!isProductOutOfStock(selectedProduct) ? (
                  <button onClick={() => addToCart(selectedProduct)} style={{ ...S.addBtn(false), width: 'auto', padding: '12px 24px', fontSize: 14 }}>
                    🛒 Adicionar ao carrinho
                  </button>
                ) : (
                  <button onClick={() => registerNotifyMe(selectedProduct)} style={{ ...S.notifyBtn, width: 'auto', padding: '10px 20px', fontSize: 13 }}>
                    🔔 Avise-me quando chegar
                  </button>
                )}
                <button onClick={() => toggleWishlist(selectedProduct.id)} style={{ background: '#fff', border: '1.5px solid #f97316', color: '#f97316', borderRadius: 9, padding: '10px 16px', fontWeight: 700, fontSize: 13, cursor: 'pointer' }}>
                  {wishlist.includes(selectedProduct.id) ? '💔 Remover' : '🤍 Salvar'}
                </button>
                <button onClick={() => { closeProductModal(); setView('carrinho'); }} style={{ background: '#fff', border: '1.5px solid #e5e7eb', color: '#6b7280', borderRadius: 9, padding: '10px 16px', fontWeight: 500, fontSize: 13, cursor: 'pointer' }}>
                  Ver carrinho
                </button>
              </div>

              <button
                onClick={() => {
                  const url = `${window.location.origin}${location.pathname}?produto=${selectedProduct.id}`;
                  navigator.clipboard?.writeText(url).then(() => setSuccess('Link copiado!')).catch(() => setSuccess(`Link: ${url}`));
                }}
                style={{ background: 'transparent', border: '1px solid #e5e7eb', color: '#9ca3af', borderRadius: 8, padding: '8px 12px', cursor: 'pointer', fontSize: 12, justifySelf: 'start' }}
              >
                🔗 Copiar link do produto
              </button>
            </div>
          </div>
        </div>
      )}

      {view === 'carrinho' && (
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 16px', minHeight: 200 }}>
          <h2 style={{ margin: '0 0 20px', fontSize: 26, fontWeight: 800, color: '#1c1917' }}>Carrinho ({cart?.itens?.length || 0} {cart?.itens?.length === 1 ? 'item' : 'itens'})</h2>
          {cartLoading ? (
            <div style={{ textAlign: 'center', color: '#64748b', padding: 40 }}>Carregando carrinho...</div>
          ) : cart?.itens?.length ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20, alignItems: 'start' }}>
              {/* Lista de itens */}
              <div style={{ display: 'grid', gap: 12 }}>
                {cart.itens.map((item) => {
                  const prod = productMap[item.produto_id];
                  const img = prod ? getProductImages(prod)[0] : null;
                  return (
                    <div key={item.item_id} style={S.cartItem}>
                      <div style={S.cartItemImg}>
                        {img ? <img src={img} alt={item.nome} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 4 }} /> : <span style={{ fontSize: 28 }}>📦</span>}
                      </div>
                      <div style={{ flex: 1, minWidth: 0, display: 'grid', gap: 4 }}>
                        <div style={{ fontWeight: 700, fontSize: 14, lineHeight: 1.3, color: '#1a1a2e' }}>{item.nome}</div>
                        <div style={{ fontSize: 13, color: '#f97316', fontWeight: 700 }}>{formatCurrency(item.preco_unitario)} / un</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                          <button onClick={() => updateCartItem(item.item_id, item.quantidade - 1)} style={S.qtyBtn}>−</button>
                          <span style={{ fontWeight: 700, fontSize: 14, minWidth: 26, textAlign: 'center' }}>{item.quantidade}</span>
                          <button onClick={() => updateCartItem(item.item_id, item.quantidade + 1)} style={S.qtyBtn}>+</button>
                          <button onClick={() => updateCartItem(item.item_id, 0)} style={S.removeBtn}>🗑 Remover</button>
                        </div>
                      </div>
                      <div style={{ fontWeight: 800, fontSize: 16, color: '#1a1a2e', flexShrink: 0 }}>
                        {formatCurrency(item.preco_unitario * item.quantidade)}
                      </div>
                    </div>
                  );
                })}

                {/* Cupom */}
                <form onSubmit={applyCupom} style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <input value={cupom} onChange={(e) => setCupom(e.target.value)} placeholder="Código de cupom" style={{ ...S.formInput, flex: 1 }} />
                  <button type="submit" style={{ background: '#f1f5f9', border: '1.5px solid #e5e7eb', color: '#374151', borderRadius: 10, padding: '0 18px', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Aplicar</button>
                </form>
                {cupomResult && (
                  <div style={{ fontSize: 13, color: '#065f46', background: '#ecfdf5', borderRadius: 8, padding: '8px 12px', fontWeight: 600 }}>
                    ✓ Cupom {cupomResult.codigo}: -{formatCurrency(cupomResult.desconto)}
                  </div>
                )}
              </div>

              {/* Resumo lateral */}
              <div style={{ background: '#fff', border: '1px solid #e7e5e4', borderRadius: 16, padding: 20, boxShadow: '0 2px 12px rgba(0,0,0,0.06)' }}>
                <div style={{ fontWeight: 700, fontSize: 16, color: '#1c1917', marginBottom: 14 }}>Resumo do pedido</div>
                {cart.itens.map((item) => (
                  <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6b7280', marginBottom: 6 }}>
                    <span>{item.nome} × {item.quantidade}</span>
                    <span>{formatCurrency(item.preco_unitario * item.quantidade)}</span>
                  </div>
                ))}
                <div style={S.cartTotalRow}>
                  <span>Total</span>
                  <span>{formatCurrency(cartTotal)}</span>
                </div>
                <button onClick={handleCheckoutFromLoja} style={{ ...S.checkoutBig, width: '100%', marginTop: 14 }}>
                  Ir para o checkout →
                </button>
                <button onClick={() => setView('loja')} style={{ width: '100%', marginTop: 8, background: 'transparent', border: '1.5px solid #e5e7eb', color: '#6b7280', borderRadius: 10, padding: '10px 0', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
                  Continuar comprando
                </button>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '48px 0', display: 'grid', gap: 12, justifyItems: 'center' }}>
              <span style={{ fontSize: 52 }}>🛒</span>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a2e' }}>Seu carrinho está vazio</div>
              <div style={{ fontSize: 14, color: '#9ca3af' }}>Explore nossa loja e adicione produtos!</div>
              <button onClick={() => setView('loja')} style={{ ...S.checkoutBig, width: 'auto', padding: '12px 28px' }}>Ver produtos</button>
            </div>
          )}
        </div>
      )}

      {view === 'checkout' && (
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 16px' }}>
          <h2 style={{ margin: '0 0 20px', fontSize: 26, fontWeight: 800, color: '#1c1917' }}>Checkout</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20, alignItems: 'start' }}>

            {/* Formulário */}
            <div style={{ display: 'grid', gap: 16 }}>
              {/* Entrega ou Retirada */}
              <div style={S.formCard}>
                <div style={{ fontWeight: 700, fontSize: 15, color: '#1a1a2e', marginBottom: 12 }}>📦 Como quer receber?</div>
                <form onSubmit={calcularResumoCheckout} style={{ display: 'grid', gap: 10 }}>
                  <div style={{ display: 'flex', gap: 10 }}>
                    {[{ v: 'entrega', l: '🚚 Entrega' }, { v: 'retirada', l: '🏪 Retirada na loja' }].map(({ v, l }) => (
                      <label key={v} style={deliveryMode === v ? S.radioLabelActive : S.radioLabel}>
                        <input type="radio" name="deliveryMode" value={v} checked={deliveryMode === v} onChange={() => setDeliveryMode(v)} style={{ display: 'none' }} />
                        {l}
                      </label>
                    ))}
                  </div>

                  {deliveryMode === 'retirada' && (
                    <div style={{ background: '#faf7f4', border: '1px solid #e7e5e4', borderRadius: 10, padding: 14, display: 'grid', gap: 8 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>Quem vai retirar?</div>
                      {[{ v: 'proprio', l: '🙋 Eu mesmo(a)' }, { v: 'terceiro', l: '🤝 Outra pessoa por mim' }].map(({ v, l }) => (
                        <label key={v} style={tipoRetirada === v ? S.radioLabelActive : S.radioLabel}>
                          <input type="radio" name="tipoRetirada" value={v} checked={tipoRetirada === v} onChange={() => setTipoRetirada(v)} style={{ display: 'none' }} />
                          {l}
                        </label>
                      ))}
                      {tipoRetirada === 'terceiro' && (
                        <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8, padding: 10, fontSize: 12, color: '#92400e' }}>
                          ℹ️ Uma <strong>senha secreta de retirada</strong> será gerada. Compartilhe com quem vai buscar.
                        </div>
                      )}
                    </div>
                  )}

                  <input value={tenantContext?.cidade || cidadeDestino} onChange={(e) => setCidadeDestino(e.target.value)} placeholder="Cidade da loja" disabled={Boolean(tenantContext?.cidade)} style={{ ...S.formInput, background: tenantContext?.cidade ? '#f8fafc' : '#fff' }} />

                  {deliveryMode === 'entrega' && (
                    <>
                      <input value={addressFields.cep} onChange={(e) => setAddressFields((prev) => ({ ...prev, cep: e.target.value }))} onBlur={handleCheckoutCepBlur} placeholder="CEP" style={S.formInput} />
                      <input value={addressFields.endereco} onChange={(e) => setAddressFields((prev) => ({ ...prev, endereco: e.target.value }))} placeholder="Rua / Avenida" style={S.formInput} />
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        <input value={addressFields.numero} onChange={(e) => setAddressFields((prev) => ({ ...prev, numero: e.target.value }))} placeholder="Número" style={S.formInput} />
                        <input value={addressFields.complemento} onChange={(e) => setAddressFields((prev) => ({ ...prev, complemento: e.target.value }))} placeholder="Complemento" style={S.formInput} />
                      </div>
                      <input value={addressFields.bairro} onChange={(e) => setAddressFields((prev) => ({ ...prev, bairro: e.target.value }))} placeholder="Bairro" style={S.formInput} />
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 8 }}>
                        <input value={addressFields.cidade || tenantContext?.cidade || ''} onChange={(e) => setAddressFields((prev) => ({ ...prev, cidade: e.target.value }))} placeholder="Cidade" disabled={Boolean(tenantContext?.cidade)} style={{ ...S.formInput, background: tenantContext?.cidade ? '#f8fafc' : '#fff' }} />
                        <input value={addressFields.estado || tenantContext?.uf || ''} onChange={(e) => setAddressFields((prev) => ({ ...prev, estado: e.target.value }))} placeholder="UF" style={S.formInput} />
                      </div>
                    </>
                  )}
                  <button type="submit" style={S.payBtn(true)}>Calcular resumo</button>
                </form>
              </div>

              {/* Pagamento */}
              <div style={S.formCard}>
                <div style={{ fontWeight: 700, fontSize: 15, color: '#1a1a2e', marginBottom: 12 }}>💳 Como vai pagar?</div>
                {(() => {
                  const opcs = [{ key: 'dinheiro', label: 'Dinheiro', icon: '💵' }, { key: 'pix', label: 'PIX', icon: '📱' }, { key: 'debito', label: 'Débito', icon: '💳' }, { key: 'credito', label: 'Crédito', icon: '💳' }];
                  const bandeiras = ['Visa', 'Mastercard', 'Elo', 'Outra'];
                  return (
                    <div style={{ display: 'grid', gap: 10 }}>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {opcs.map((o) => (
                          <label key={o.key} style={pagamentoTipo === o.key ? S.radioLabelActive : S.radioLabel}>
                            <input type="radio" name="pagamentoTipo" value={o.key} checked={pagamentoTipo === o.key} onChange={() => { setPagamentoTipo(o.key); if (o.key !== 'dinheiro') setPagamentoTroco(''); }} style={{ display: 'none' }} />
                            {o.icon} {o.label}
                          </label>
                        ))}
                      </div>
                      {pagamentoTipo === 'dinheiro' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                          <span style={{ color: '#374151' }}>Troco para R$</span>
                          <input type="number" min="0" placeholder="Ex: 100" value={pagamentoTroco} onChange={(e) => setPagamentoTroco(e.target.value)} style={{ ...S.formInput, width: 110 }} />
                        </div>
                      )}
                      {(pagamentoTipo === 'debito' || pagamentoTipo === 'credito') && (
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                          <span style={{ fontSize: 13, color: '#6b7280' }}>Bandeira:</span>
                          {bandeiras.map((b) => (
                            <label key={b} style={pagamentoBandeira === b ? S.radioLabelActive : { ...S.radioLabel, padding: '6px 12px', fontSize: 12 }}>
                              <input type="radio" checked={pagamentoBandeira === b} onChange={() => setPagamentoBandeira(b)} style={{ display: 'none' }} /> {b}
                            </label>
                          ))}
                        </div>
                      )}
                      {pagamentoTipo === 'credito' && (
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <span style={{ fontSize: 13, color: '#6b7280' }}>Parcelas:</span>
                          {[1, 2, 3].map((p) => (
                            <label key={p} style={pagamentoParcelas === p ? S.radioLabelActive : { ...S.radioLabel, padding: '6px 14px' }}>
                              <input type="radio" checked={pagamentoParcelas === p} onChange={() => setPagamentoParcelas(p)} style={{ display: 'none' }} /> {p}x
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Resumo lateral */}
            <div style={S.resumoBox}>
              <div style={{ fontWeight: 700, fontSize: 16, color: '#1c1917', marginBottom: 14 }}>Resumo do pedido</div>
              {checkoutResumo ? (
                <div style={{ display: 'grid', gap: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6b7280' }}><span>Itens ({checkoutResumo.itens_count})</span><span>{formatCurrency(checkoutResumo.subtotal)}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6b7280' }}><span>Frete</span><span>{formatCurrency(checkoutResumo?.frete?.valor_frete)}</span></div>
                  {checkoutResumo?.cupom?.desconto > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#065f46' }}><span>Desconto</span><span>-{formatCurrency(checkoutResumo.cupom.desconto)}</span></div>
                  )}
                  <div style={S.cartTotalRow}><span>Total</span><span>{formatCurrency(checkoutResumo.total)}</span></div>
                </div>
              ) : (
                cart?.itens?.length ? (
                  <div>
                    {cart.itens.map((item) => (
                      <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6b7280', marginBottom: 6 }}>
                        <span>{item.nome} × {item.quantidade}</span>
                        <span>{formatCurrency(item.preco_unitario * item.quantidade)}</span>
                      </div>
                    ))}
                    <div style={S.cartTotalRow}><span>Total estimado</span><span>{formatCurrency(cartTotal)}</span></div>
                  </div>
                ) : null
              )}

              <button onClick={finalizarCheckout} disabled={checkoutLoading || !(tenantContext?.cidade || cidadeDestino) || !cart?.itens?.length || !isProfileComplete} style={S.finalizarBtn(checkoutLoading || !(tenantContext?.cidade || cidadeDestino) || !cart?.itens?.length || !isProfileComplete)}>
                {checkoutLoading ? 'Finalizando...' : '✓ Finalizar pedido'}
              </button>

              {!isProfileComplete && (
                <div style={{ fontSize: 12, color: '#b45309', background: '#fffbeb', borderRadius: 8, padding: '8px 10px', marginTop: 6 }}>
                  ⚠️ Complete seu cadastro (nome, telefone, CPF e endereço) na aba Conta para finalizar.
                </div>
              )}

              {checkoutResult?.pedido_id && (
                <div style={{ background: '#ecfdf5', border: '1.5px solid #6ee7b7', borderRadius: 12, padding: 14, marginTop: 8, display: 'grid', gap: 6 }}>
                  <div style={{ fontWeight: 700, color: '#065f46', fontSize: 14 }}>✓ Pedido confirmado!</div>
                  <div style={{ fontSize: 13, color: '#374151' }}>Número: <strong>{checkoutResult.pedido_id}</strong></div>
                  {checkoutResult.palavra_chave_retirada && (
                    <div style={{ background: '#fff7ed', border: '2px solid #f97316', borderRadius: 10, padding: 12, textAlign: 'center', marginTop: 4 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#7c2d12', marginBottom: 4 }}>🔑 SENHA DE RETIRADA</div>
                      <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: 3, color: '#ea580c' }}>{checkoutResult.palavra_chave_retirada}</div>
                      <div style={{ fontSize: 11, color: '#92400e', marginTop: 4 }}>Compartilhe com quem vai retirar</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {view === 'pedidos' && (
        <div style={{ maxWidth: 900, margin: '0 auto', padding: '28px 16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 10 }}>
            <h2 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: '#1c1917' }}>Meus Pedidos</h2>
            <button onClick={loadOrdersDetailed} disabled={ordersLoading} style={{ background: '#f1f5f9', border: '1.5px solid #e5e7eb', color: '#374151', borderRadius: 10, padding: '8px 16px', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
              {ordersLoading ? 'Atualizando...' : '↻ Atualizar'}
            </button>
          </div>
          {ordersLoading ? (
            <div style={{ textAlign: 'center', color: '#64748b', padding: 40 }}>Carregando pedidos...</div>
          ) : ordersDetailed.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 0', display: 'grid', gap: 10, justifyItems: 'center' }}>
              <span style={{ fontSize: 48 }}>📋</span>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a2e' }}>Nenhum pedido ainda</div>
              <div style={{ fontSize: 13, color: '#9ca3af' }}>Seus pedidos aparecerão aqui após a compra.</div>
              <button onClick={() => setView('loja')} style={{ ...S.checkoutBig, width: 'auto', padding: '10px 24px' }}>Ir às compras</button>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 14 }}>
              {ordersDetailed.map((order) => {
                const statusMap = { pendente: '#f59e0b', confirmado: '#3b82f6', enviado: '#8b5cf6', entregue: '#10b981', cancelado: '#ef4444' };
                const statusColor = statusMap[(order.status || '').toLowerCase()] || '#6b7280';
                return (
                  <div key={order.pedido_id} style={S.orderCard}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 14, color: '#1a1a2e', marginBottom: 2 }}>Pedido {order.pedido_id}</div>
                        <div style={{ fontSize: 12, color: '#9ca3af' }}>{order.created_at ? new Date(order.created_at).toLocaleString('pt-BR') : '-'}</div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                        <span style={{ ...S.statusBadge(order.status), background: statusColor + '20', color: statusColor, border: `1px solid ${statusColor}40` }}>{order.status || 'Pendente'}</span>
                        <div style={{ fontWeight: 800, fontSize: 16, color: '#1a1a2e' }}>{formatCurrency(order.total)}</div>
                      </div>
                    </div>

                    {order.palavra_chave_retirada && (
                      <div style={{ background: '#fff7ed', border: '2px solid #f97316', borderRadius: 10, padding: 10, textAlign: 'center', marginTop: 8 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#7c2d12', marginBottom: 2 }}>🔑 SENHA DE RETIRADA</div>
                        <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: 3, color: '#ea580c' }}>{order.palavra_chave_retirada}</div>
                        <div style={{ fontSize: 10, color: '#92400e', marginTop: 2 }}>Apresente na loja para retirar</div>
                      </div>
                    )}

                    {Array.isArray(order.itens) && order.itens.length > 0 && (
                      <div style={{ marginTop: 10, borderTop: '1px solid #f1f5f9', paddingTop: 10, display: 'grid', gap: 6 }}>
                        {order.itens.map((item, index) => (
                          <div key={`${order.pedido_id}-${item.produto_id || index}`} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6b7280' }}>
                            <span>{item.nome || 'Produto'} × {item.quantidade}</span>
                            <span>{formatCurrency(item.subtotal)}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {order.data_pagamento && (
                      <div style={{ fontSize: 12, color: '#6b7280', marginTop: 6 }}>Pago em: {formatDateTime(order.data_pagamento)}</div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      {view === 'conta' && (
        <div style={{ maxWidth: 900, margin: '0 auto', padding: '28px 16px' }}>
          <h2 style={{ margin: '0 0 20px', fontSize: 26, fontWeight: 800, color: '#1c1917' }}>Minha Conta</h2>
          {customerToken ? (
            <div style={{ display: 'grid', gap: 16 }}>
              <div style={S.accountCard}>
                <div style={{ fontWeight: 700, fontSize: 15, color: '#1a1a2e', marginBottom: 4 }}>Olá, {customer?.nome || profileForm.nome || 'cliente'}! 👋</div>
                <div style={{ fontSize: 13, color: '#9ca3af', marginBottom: 14 }}>
                  {customer?.email} • Lista de desejos: {wishlist.length} • Avisos: {notifyRequests.length}
                </div>

                <form onSubmit={saveProfile} style={{ display: 'grid', gap: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, color: '#374151', marginBottom: 2 }}>Dados pessoais</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <input value={profileForm.nome} onChange={(e) => setProfileForm((prev) => ({ ...prev, nome: e.target.value }))} placeholder="Nome completo" style={S.formInput} />
                    <input value={customer?.email || ''} disabled placeholder="Email" style={{ ...S.formInput, background: '#f8fafc', color: '#9ca3af' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <input value={profileForm.telefone} onChange={(e) => setProfileForm((prev) => ({ ...prev, telefone: e.target.value }))} placeholder="Telefone" style={S.formInput} />
                    <input value={profileForm.cpf} onChange={(e) => setProfileForm((prev) => ({ ...prev, cpf: e.target.value }))} placeholder="CPF" style={S.formInput} />
                  </div>

                  <div style={{ fontWeight: 600, fontSize: 13, color: '#374151', marginTop: 6, marginBottom: 2 }}>Endereço principal</div>
                  <input value={profileForm.cep} onChange={(e) => setProfileForm((prev) => ({ ...prev, cep: e.target.value }))} onBlur={handleProfileCepBlur} placeholder="CEP" style={S.formInput} />
                  <input value={profileForm.endereco} onChange={(e) => setProfileForm((prev) => ({ ...prev, endereco: e.target.value }))} placeholder="Rua / Avenida" style={S.formInput} />
                  <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 8 }}>
                    <input value={profileForm.numero} onChange={(e) => setProfileForm((prev) => ({ ...prev, numero: e.target.value }))} placeholder="Número" style={S.formInput} />
                    <input value={profileForm.complemento} onChange={(e) => setProfileForm((prev) => ({ ...prev, complemento: e.target.value }))} placeholder="Complemento" style={S.formInput} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 100px', gap: 8 }}>
                    <input value={profileForm.bairro} onChange={(e) => setProfileForm((prev) => ({ ...prev, bairro: e.target.value }))} placeholder="Bairro" style={S.formInput} />
                    <input value={profileForm.cidade} onChange={(e) => setProfileForm((prev) => ({ ...prev, cidade: e.target.value }))} placeholder="Cidade" style={S.formInput} />
                    <input value={profileForm.estado} onChange={(e) => setProfileForm((prev) => ({ ...prev, estado: e.target.value }))} placeholder="UF" style={S.formInput} />
                  </div>

                  <button type="button" onClick={() => setProfileForm((prev) => ({ ...prev, usar_endereco_entrega_diferente: !prev.usar_endereco_entrega_diferente }))} style={{ justifySelf: 'start', background: 'transparent', border: '1.5px solid #e7e5e4', color: '#f97316', borderRadius: 8, padding: '8px 14px', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
                    {profileForm.usar_endereco_entrega_diferente ? '− Remover endereço alternativo' : '+ Adicionar endereço de entrega diferente'}
                  </button>

                  {profileForm.usar_endereco_entrega_diferente && (
                    <div style={{ display: 'grid', gap: 8, background: '#faf7f4', border: '1px solid #e7e5e4', borderRadius: 12, padding: 14 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>Endereço de entrega alternativo</div>
                      <input value={profileForm.entrega_nome} onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_nome: e.target.value }))} placeholder="Nome para entrega" style={S.formInput} />
                      <input value={profileForm.entrega_cep} onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_cep: e.target.value }))} onBlur={handleDeliveryCepBlur} placeholder="CEP" style={S.formInput} />
                      <input value={profileForm.entrega_endereco} onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_endereco: e.target.value }))} placeholder="Rua / Avenida" style={S.formInput} />
                      <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 8 }}>
                        <input value={profileForm.entrega_numero} onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_numero: e.target.value }))} placeholder="Número" style={S.formInput} />
                        <input value={profileForm.entrega_complemento} onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_complemento: e.target.value }))} placeholder="Complemento" style={S.formInput} />
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 100px', gap: 8 }}>
                        <input value={profileForm.entrega_bairro} onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_bairro: e.target.value }))} placeholder="Bairro" style={S.formInput} />
                        <input value={profileForm.entrega_cidade} onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_cidade: e.target.value }))} placeholder="Cidade" style={S.formInput} />
                        <input value={profileForm.entrega_estado} onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_estado: e.target.value }))} placeholder="UF" style={S.formInput} />
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button type="submit" disabled={profileSaving} style={S.saveBtn}>
                      {profileSaving ? 'Salvando...' : '✓ Salvar cadastro'}
                    </button>
                    <button type="button" onClick={logoutCustomer} style={{ background: '#f1f5f9', border: '1.5px solid #e5e7eb', color: '#ef4444', borderRadius: 10, padding: '10px 20px', fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>
                      Sair da conta
                    </button>
                  </div>
                </form>
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              {/* Cadastro */}
              <div style={S.accountCard}>
                <div style={{ fontWeight: 800, fontSize: 20, color: '#1c1917', marginBottom: 14 }}>Criar conta</div>
                <form onSubmit={handleRegister} autoComplete="off" style={{ display: 'grid', gap: 10 }}>
                  <input name="ecommerce_register_nome" autoComplete="off" value={registerForm.nome} onChange={(e) => setRegisterForm((prev) => ({ ...prev, nome: e.target.value }))} placeholder="Nome completo" style={S.formInput} />
                  <input name="ecommerce_register_email" autoComplete="off" value={registerForm.email} onChange={(e) => setRegisterForm((prev) => ({ ...prev, email: e.target.value }))} placeholder="Email" type="email" style={S.formInput} />
                  <div style={{ position: 'relative' }}>
                    <input name="ecommerce_register_password" autoComplete="new-password" value={registerForm.password} onChange={(e) => setRegisterForm((prev) => ({ ...prev, password: e.target.value }))} placeholder="Senha" type={showRegisterPassword ? 'text' : 'password'} style={{ ...S.formInput, paddingRight: 80, width: '100%', boxSizing: 'border-box' }} />
                    <button type="button" onClick={() => setShowRegisterPassword((prev) => !prev)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: '#6b7280' }}>
                      {showRegisterPassword ? 'Ocultar' : '👁 Ver'}
                    </button>
                  </div>
                  <button type="submit" disabled={authLoading} style={S.saveBtn}>{authLoading ? 'Criando...' : 'Criar minha conta'}</button>
                </form>
              </div>

              {/* Login */}
              <div style={S.accountCard}>
                <div style={{ fontWeight: 800, fontSize: 20, color: '#1c1917', marginBottom: 14 }}>Entrar</div>
                <form onSubmit={handleLogin} autoComplete="off" style={{ display: 'grid', gap: 10 }}>
                  <input name="ecommerce_login_email" autoComplete="off" value={loginForm.email} onChange={(e) => setLoginForm((prev) => ({ ...prev, email: e.target.value }))} placeholder="Email" type="email" style={S.formInput} />
                  <div style={{ position: 'relative' }}>
                    <input name="ecommerce_login_password" autoComplete="new-password" value={loginForm.password} onChange={(e) => setLoginForm((prev) => ({ ...prev, password: e.target.value }))} placeholder="Senha" type={showLoginPassword ? 'text' : 'password'} style={{ ...S.formInput, paddingRight: 80, width: '100%', boxSizing: 'border-box' }} />
                    <button type="button" onClick={() => setShowLoginPassword((prev) => !prev)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: '#6b7280' }}>
                      {showLoginPassword ? 'Ocultar' : '👁 Ver'}
                    </button>
                  </div>
                  <button type="submit" disabled={authLoading} style={S.saveBtn}>{authLoading ? 'Entrando...' : 'Entrar'}</button>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Modal Avise-me ── */}
      {notifyMeModal.open && (
        <div
          role="dialog"
          aria-modal="true"
          style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
          onClick={() => setNotifyMeModal({ open: false, product: null, email: '', loading: false })}
        >
          <div
            style={{ background: '#fff', borderRadius: 18, padding: 28, maxWidth: 380, width: '100%', boxShadow: '0 24px 80px rgba(0,0,0,0.25)', border: '1px solid #e5e7eb' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ fontSize: 32, marginBottom: 8 }}>🔔</div>
            <h3 style={{ margin: '0 0 8px', fontSize: 18, fontWeight: 800, color: '#1c1917' }}>Avise-me quando chegar</h3>
            <p style={{ margin: '0 0 18px', fontSize: 14, color: '#6b7280' }}>
              <strong>{notifyMeModal.product?.nome}</strong> está sem estoque agora. Informe seu email e te avisamos quando voltar!
            </p>
            <form onSubmit={submitNotifyMe} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <input type="email" required placeholder="seu@email.com" value={notifyMeModal.email} autoFocus onChange={(e) => setNotifyMeModal((prev) => ({ ...prev, email: e.target.value }))} style={S.formInput} />
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="button" onClick={() => setNotifyMeModal({ open: false, product: null, email: '', loading: false })} style={{ flex: 1, padding: '10px 0', borderRadius: 10, border: '1.5px solid #e5e7eb', background: '#fff', color: '#374151', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>Cancelar</button>
                <button type="submit" disabled={notifyMeModal.loading} style={{ flex: 2, padding: '10px 0', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer', opacity: notifyMeModal.loading ? 0.7 : 1 }}>
                  {notifyMeModal.loading ? 'Registrando…' : '🔔 Me avise!'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Footer ── */}
      <footer style={S.footer}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 28 }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 20, color: '#fff', marginBottom: 8 }}>
              🐾 {tenantContext?.nome_fantasia || tenantContext?.nome || 'Pet Store'}
            </div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
              Produtos de qualidade para o seu pet com carinho e dedicação. Compre online com facilidade!
            </div>
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.85)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Navegação</div>
            {[{ l: '🛍️ Loja', v: 'loja' }, { l: '🛒 Carrinho', v: 'carrinho' }, { l: '📦 Pedidos', v: 'pedidos' }, { l: '👤 Conta', v: 'conta' }].map(({ l, v }) => (
              <button key={v} onClick={() => setView(v)} style={{ display: 'block', background: 'none', border: 'none', color: 'rgba(255,255,255,0.65)', fontSize: 13, cursor: 'pointer', padding: '3px 0', textAlign: 'left' }}>{l}</button>
            ))}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.85)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Contato</div>
            {tenantContext?.whatsapp && (
              <a href={`https://wa.me/55${tenantContext.whatsapp.replace(/\D/g, '')}`} target="_blank" rel="noreferrer" style={{ display: 'block', color: 'rgba(255,255,255,0.65)', fontSize: 13, textDecoration: 'none', marginBottom: 4 }}>📱 WhatsApp</a>
            )}
            {tenantContext?.email && (
              <a href={`mailto:${tenantContext.email}`} style={{ display: 'block', color: 'rgba(255,255,255,0.65)', fontSize: 13, textDecoration: 'none' }}>✉️ {tenantContext.email}</a>
            )}
            {tenantContext?.cidade && (
              <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12, marginTop: 8 }}>📍 {tenantContext.cidade}{tenantContext.uf ? `, ${tenantContext.uf}` : ''}</div>
            )}
          </div>
        </div>
        <div style={{ maxWidth: 1100, margin: '20px auto 0', paddingTop: 16, borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: 12, color: 'rgba(255,255,255,0.4)', textAlign: 'center' }}>
          © {new Date().getFullYear()} {tenantContext?.nome_fantasia || tenantContext?.nome || 'Pet Store'}. Todos os direitos reservados.
        </div>
      </footer>
    </div>
  );
}
