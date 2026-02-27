import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import ecommerceApi from '../../services/ecommerceApi';
import { api } from '../../services/api';

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
    bg: 'linear-gradient(135deg, #c41c1c 0%, #9b1515 60%, #7a0f0f 100%)',
    title: 'Compre e receba no mesmo dia!',
    sub: 'Pedidos realizados até as 16h',
    emoji: '🚀',
  },
  {
    bg: 'linear-gradient(135deg, #2e7d32 0%, #388e3c 60%, #43a047 100%)',
    title: 'Retire na loja',
    sub: 'Super simples e sem custo de frete!',
    emoji: '🏪',
  },
  {
    bg: 'linear-gradient(135deg, #d97706 0%, #b45309 60%, #92400e 100%)',
    title: 'As melhores rações em Prudente',
    sub: 'Cachorros, gatos, pássaros e mais 🐾',
    emoji: '🐶',
  },
];

export default function EcommerceMVP() {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  const [view, setView] = useState('loja');
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
      const categoriaNome = item?.categoria_nome || item?.categoria || 'Sem categoria';
      const matchesSearch = !query || nome.includes(query);
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
    const informedEmail = window.prompt('Digite seu email para avisarmos quando chegar em estoque:', fallbackEmail);
    if (!informedEmail) return;

    const request = {
      productId: product.id,
      productName: product.nome,
      email: informedEmail.trim(),
      tenant: storefrontRef || tenantRef,
      createdAt: new Date().toISOString(),
    };

    setNotifyRequests((prev) => {
      const exists = prev.some(
        (item) => item.productId === request.productId && String(item.email || '').toLowerCase() === request.email.toLowerCase()
      );
      if (exists) return prev;
      return [...prev, request];
    });

    setSuccess('Aviso registrado. Quando chegar estoque, você será notificado por email.');
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
  }

  function openProductDetails(product) {
    const images = getProductImages(product);
    setSelectedProduct(product);
    setActiveProductImage(images[0] || '');
  }

  return (
    <div className="page">

      {/* BARRA DE CARRINHO FLUTUANTE */}
      {cart?.itens?.length > 0 && (
        <div
          onClick={() => setView('carrinho')}
          style={{ position: 'sticky', top: 0, zIndex: 50, background: '#c41c1c', color: '#fff', padding: '9px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderRadius: 10, marginBottom: 10, cursor: 'pointer', boxShadow: '0 3px 12px rgba(196,28,28,0.45)' }}
        >
          <span style={{ fontWeight: 600, fontSize: 14 }}>🛒 {cart.itens.length} item(ns) no carrinho</span>
          <span style={{ fontWeight: 800, fontSize: 14 }}>{formatCurrency(cartTotal)} →</span>
        </div>
      )}

      {/* HEADER */}
      <div
        style={{
          background: 'linear-gradient(135deg, #fff8e1 0%, #fff3cd 100%)',
          borderRadius: 16,
          padding: '16px 20px',
          marginBottom: 10,
          border: '1px solid #fde68a',
          boxShadow: '0 2px 8px rgba(196,28,28,0.07)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 11, color: '#92400e', fontWeight: 700, letterSpacing: 1.2, textTransform: 'uppercase' }}>Loja Online</div>
            {tenantContext?.logo_url ? (
              <img
                src={resolveMediaUrl(tenantContext.logo_url)}
                alt={storeDisplayName}
                style={{ maxHeight: 56, maxWidth: 200, objectFit: 'contain', margin: '4px 0' }}
              />
            ) : (
              <h1 style={{ margin: '2px 0 4px', fontSize: 30, lineHeight: 1.1, color: '#c41c1c', fontWeight: 900 }}>{storeDisplayName}</h1>
            )}
            <div style={{ fontSize: 13, color: '#78350f', fontWeight: 500 }}>
              📍 {tenantContext?.cidade || 'Cidade não informada'}{tenantContext?.uf ? ` • ${tenantContext.uf}` : ''}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {customerDisplayName ? (
              <div style={{ fontSize: 13, color: '#374151', background: '#fff', borderRadius: 20, padding: '6px 12px', border: '1px solid #d1d5db', fontWeight: 600 }}>
                👤 {customerDisplayName.split(' ')[0]}
              </div>
            ) : (
              <button onClick={() => setView('conta')} style={{ background: '#fff', border: '2px solid #2e7d32', color: '#2e7d32', borderRadius: 20, padding: '6px 14px', cursor: 'pointer', fontSize: 13, fontWeight: 700 }}>
                Entrar / Cadastrar
              </button>
            )}
            <button
              onClick={() => setView('carrinho')}
              style={{ background: '#c41c1c', color: '#fff', border: 'none', borderRadius: 50, width: 48, height: 48, cursor: 'pointer', fontSize: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', boxShadow: '0 2px 8px rgba(196,28,28,0.4)', flexShrink: 0 }}
            >
              🛒
              {cart?.itens?.length > 0 && (
                <span style={{ position: 'absolute', top: -4, right: -4, background: '#f5a623', color: '#7c2d12', borderRadius: 50, minWidth: 20, height: 20, fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #fff', padding: '0 3px' }}>
                  {cart.itens.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* BANNER ROTATIVO */}
      <div style={{ position: 'relative', borderRadius: 14, overflow: 'hidden', marginBottom: 10, height: 112 }}>
        {activeBanners.map((b, i) => (
          <div
            key={i}
            style={{
              position: 'absolute', inset: 0,
              opacity: bannerSlide === i ? 1 : 0,
              transition: 'opacity 0.8s ease',
              pointerEvents: bannerSlide === i ? 'auto' : 'none',
            }}
          >
            {b.type === 'image' ? (
              <img src={resolveMediaUrl(b.url)} alt={`Banner ${i + 1}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <div style={{ background: b.bg, display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16, height: '100%' }}>
                <span style={{ fontSize: 44, flexShrink: 0 }}>{b.emoji}</span>
                <div>
                  <div style={{ color: '#fff', fontWeight: 900, fontSize: 20, lineHeight: 1.2, textShadow: '0 1px 3px rgba(0,0,0,0.25)' }}>{b.title}</div>
                  <div style={{ color: 'rgba(255,255,255,0.88)', fontSize: 13, marginTop: 5 }}>{b.sub}</div>
                </div>
              </div>
            )}
          </div>
        ))}
        <div style={{ position: 'absolute', bottom: 9, right: 14, display: 'flex', gap: 5 }}>
          {activeBanners.map((_, i) => (
            <button
              key={i}
              onClick={() => setBannerSlide(i)}
              style={{ width: bannerSlide === i ? 22 : 8, height: 8, background: bannerSlide === i ? '#fff' : 'rgba(255,255,255,0.5)', borderRadius: 4, border: 'none', cursor: 'pointer', padding: 0, transition: 'all 0.3s ease' }}
            />
          ))}
        </div>
      </div>

      {/* BANNER APP */}
      <div style={{ marginBottom: 10, background: 'linear-gradient(90deg, #2e7d32, #43a047)', color: '#fff', borderRadius: 10, padding: '10px 14px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 20 }}>📱</span>
        <span>Baixe nosso <strong>APP</strong> para notificações de pedidos, promoções e aviso de reposição de estoque.</span>
      </div>

      {!tenantRef && (
        <div style={{ marginBottom: 12, color: '#b00020' }}>
          Use a URL no formato: /slug-da-loja
        </div>
      )}

      {/* NAVEGAÇÃO */}
      <div style={{ display: 'flex', gap: 6, background: '#f0fdf4', borderRadius: 12, overflow: 'hidden', marginBottom: 16, padding: 5, border: '1px solid #bbf7d0' }}>
        {[
          ['loja', '🏪 Loja'],
          ['carrinho', `🛒 Carrinho${cart?.itens?.length ? ` (${cart.itens.length})` : ''}`],
          ['pedidos', '📦 Pedidos'],
          ['conta', '👤 Conta'],
        ].map(([tabId, label]) => {
          const active = view === tabId;
          return (
            <button
              key={tabId}
              onClick={() => setView(tabId)}
              style={{
                flex: 1,
                background: active ? '#2e7d32' : '#fff',
                color: active ? '#fff' : '#2e7d32',
                padding: '10px 4px',
                fontWeight: active ? 700 : 600,
                cursor: 'pointer',
                fontSize: 13,
                borderRadius: 8,
                boxShadow: active ? '0 2px 8px rgba(46,125,50,0.3)' : '0 1px 3px rgba(0,0,0,0.08)',
                transition: 'all 0.15s ease',
                border: active ? '1px solid #2e7d32' : '1px solid #d1fae5',
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {error && (
        <div style={{ background: '#ffe8e8', color: '#8c0000', padding: 10, borderRadius: 6, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {success && (
        <div style={{ background: '#e8fff0', color: '#0a7d32', padding: 10, borderRadius: 6, marginBottom: 12 }}>
          {success}
        </div>
      )}

      {view === 'loja' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 16 }}>
          <div style={{ background: '#fff', padding: 16, borderRadius: 12, border: '1px solid #e5e7eb' }}>
          <h3 style={{ marginTop: 0, color: '#2e7d32', fontSize: 18 }}>🔍 Catálogo da loja</h3>
              <div style={{ color: '#64748b', fontSize: 14, marginBottom: 12 }}>Selecione produtos, confira detalhes e adicione ao carrinho.</div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar produto..."
                style={{ flex: 1, minWidth: 240, padding: 10, border: '1px solid #d1d5db', borderRadius: 10 }}
              />
              <select value={categoria} onChange={(e) => setCategoria(e.target.value)} style={{ padding: 10, border: '1px solid #d1d5db', borderRadius: 10 }}>
                {categorias.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
              <button className="btn-secondary" onClick={loadProducts} disabled={loading}>
                {loading ? 'Carregando...' : 'Atualizar'}
              </button>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gap: 12,
              }}
            >
              {filteredProducts.map((product) => {
                const stock = resolveProductStock(product);
                const outOfStock = isProductOutOfStock(product);
                const wished = wishlist.includes(product.id);
                const productImage = getProductImages(product)[0];

                return (
                <div
                  role="button"
                  tabIndex={0}
                  key={product.id}
                  onClick={() => openProductDetails(product)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      openProductDetails(product);
                    }
                  }}
                  onMouseEnter={() => setHoveredCard(product.id)}
                  onMouseLeave={() => setHoveredCard(null)}
                  style={{
                    border: hoveredCard === product.id ? '2px solid #c41c1c' : '1px solid #e5e7eb',
                    borderRadius: 14,
                    padding: 10,
                    background: '#fff',
                    textAlign: 'left',
                    cursor: 'pointer',
                    display: 'grid',
                    gap: 8,
                    transition: 'all 0.18s ease',
                    boxShadow: hoveredCard === product.id ? '0 6px 20px rgba(196,28,28,0.14)' : '0 1px 4px rgba(0,0,0,0.05)',
                    transform: hoveredCard === product.id ? 'translateY(-3px)' : 'none',
                  }}
                >
                  <div
                    style={{
                      borderRadius: 10,
                      background: '#f1f5f9',
                      aspectRatio: '1 / 1',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      overflow: 'hidden',
                    }}
                  >
                    {productImage ? (
                      <img
                        src={productImage}
                        alt={product.nome}
                        style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 6, background: '#fff' }}
                      />
                    ) : (
                      <span style={{ color: '#64748b', fontSize: 12 }}>Sem imagem</span>
                    )}
                  </div>

                  <div style={{ minHeight: 42 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, lineHeight: 1.25 }}>{product.nome}</div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                      {product?.categoria_nome || product?.categoria || 'Sem categoria'}
                    </div>
                    <div style={{ fontSize: 12, color: '#475569', marginTop: 2 }}>
                      SKU: {product?.codigo || '-'}
                    </div>
                    <div style={{ fontSize: 12, color: outOfStock ? '#b45309' : '#0f766e', marginTop: 4 }}>
                      {outOfStock ? 'Volto em breve' : Number.isFinite(stock) ? `Estoque disponível: ${stock}` : 'Estoque disponível'}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <strong style={{ fontSize: 16 }}>{formatCurrency(resolveProductPrice(product))}</strong>
                    <button
                      className="btn-primary"
                      disabled={outOfStock}
                      style={{
                        background: outOfStock ? '#9ca3af' : '#c41c1c',
                        border: 'none',
                        color: '#fff',
                        borderRadius: 8,
                        padding: '8px 12px',
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: outOfStock ? 'not-allowed' : 'pointer',
                        opacity: outOfStock ? 0.75 : 1,
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        addToCart(product);
                      }}
                    >
                      {outOfStock ? 'Indisponível' : '+ Adicionar'}
                    </button>
                  </div>

                  <div style={{ display: 'flex', gap: 6, marginTop: 2 }}>
                    <button
                      className="btn-secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleWishlist(product.id);
                      }}
                      style={{ fontSize: 12, padding: '6px 8px' }}
                    >
                      {wished ? 'Remover desejo' : 'Lista de desejos'}
                    </button>
                    {outOfStock && (
                      <button
                        className="btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          registerNotifyMe(product);
                        }}
                        style={{ fontSize: 12, padding: '6px 8px' }}
                      >
                        Avise-me
                      </button>
                    )}
                  </div>
                </div>
              );})}

              {!loading && filteredProducts.length === 0 && (
                <div style={{ color: '#666', padding: 12, display: 'grid', gap: 10 }}>
                  <div>Nenhum produto encontrado para o filtro atual.</div>
                </div>
              )}
            </div>

          </div>

          <aside style={{ background: '#fff', padding: 16, borderRadius: 14, border: '1px solid #e5e7eb', alignSelf: 'start', position: 'sticky', top: 8, boxShadow: '0 2px 12px rgba(0,0,0,0.07)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 15, color: '#2e7d32' }}>🛒 Seu carrinho</h3>
              {cart?.itens?.length > 0 && (
                <span style={{ background: '#c41c1c', color: '#fff', borderRadius: 20, padding: '2px 9px', fontSize: 12, fontWeight: 700 }}>
                  {cart.itens.length}
                </span>
              )}
            </div>
            {cart?.itens?.length ? (
              <div style={{ display: 'grid', gap: 8 }}>
                {cart.itens.slice(0, 5).map((item) => {
                  const prod = productMap[item.produto_id];
                  const img = prod ? getProductImages(prod)[0] : null;
                  return (
                    <div key={item.item_id} style={{ display: 'flex', gap: 8, alignItems: 'center', borderBottom: '1px solid #f1f5f9', paddingBottom: 8, marginBottom: 2 }}>
                      <div style={{ width: 44, height: 44, borderRadius: 8, background: '#f8fafc', flexShrink: 0, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e5e7eb' }}>
                        {img ? <img src={img} alt={item.nome} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 2 }} /> : <span style={{ fontSize: 18 }}>📦</span>}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.nome}</div>
                        <div style={{ fontSize: 11, color: '#64748b' }}>{item.quantidade}× {formatCurrency(item.preco_unitario)}</div>
                      </div>
                    </div>
                  );
                })}
                {cart.itens.length > 5 && (
                  <div style={{ fontSize: 12, color: '#64748b', textAlign: 'center' }}>+ {cart.itens.length - 5} item(ns) a mais</div>
                )}
                <div style={{ background: '#fef2f2', borderRadius: 8, padding: '8px 10px', marginTop: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>Subtotal</span>
                  <span style={{ fontWeight: 800, fontSize: 16, color: '#c41c1c' }}>{formatCurrency(cartTotal)}</span>
                </div>
                <button
                  className="btn-primary"
                  onClick={handleCheckoutFromLoja}
                  style={{ background: '#c41c1c', border: 'none', color: '#fff', borderRadius: 10, padding: '11px 0', fontWeight: 700, fontSize: 14, cursor: 'pointer', width: '100%' }}
                >
                  ✅ Finalizar compra
                </button>
                <button className="btn-secondary" onClick={() => setView('carrinho')} style={{ borderRadius: 10, width: '100%' }}>Ver / Editar carrinho</button>
                {!customerToken && (
                  <div style={{ fontSize: 11, color: '#64748b', textAlign: 'center' }}>Login solicitado só no fechamento</div>
                )}
              </div>
            ) : (
              <div style={{ color: '#94a3b8', textAlign: 'center', padding: '20px 0', fontSize: 13 }}>
                <div style={{ fontSize: 30, marginBottom: 6 }}>🛒</div>
                Seu carrinho está vazio.
              </div>
            )}
          </aside>
        </div>
      )}

      {selectedProduct && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
            zIndex: 60,
          }}
          onClick={() => setSelectedProduct(null)}
        >
          <div
            style={{
              background: '#fff',
              width: 'min(980px, 100%)',
              maxHeight: '90vh',
              overflowY: 'auto',
              borderRadius: 14,
              border: '1px solid #e5e7eb',
              padding: 16,
              display: 'grid',
              gridTemplateColumns: '1.1fr 1fr',
              gap: 16,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <div
                style={{
                  borderRadius: 12,
                  background: '#f1f5f9',
                  aspectRatio: '1 / 1',
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {activeProductImage ? (
                  <img src={activeProductImage} alt={selectedProduct.nome} style={{ width: '100%', height: '100%', objectFit: 'contain', background: '#fff' }} />
                ) : (
                  <span style={{ color: '#64748b' }}>Sem imagem disponível</span>
                )}
              </div>

              {getProductImages(selectedProduct).length > 1 && (
                <div style={{ display: 'flex', gap: 8, marginTop: 10, overflowX: 'auto' }}>
                  {getProductImages(selectedProduct).map((img) => (
                    <button
                      key={img}
                      onClick={() => setActiveProductImage(img)}
                      style={{
                        border: activeProductImage === img ? '2px solid #c41c1c' : '1px solid #d1d5db',
                        borderRadius: 8,
                        width: 74,
                        height: 74,
                        overflow: 'hidden',
                        padding: 0,
                        background: '#fff',
                        cursor: 'pointer',
                      }}
                    >
                      <img src={img} alt="Miniatura do produto" style={{ width: '100%', height: '100%', objectFit: 'contain', background: '#fff' }} />
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: 'grid', alignContent: 'start', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                <h3 style={{ margin: 0, fontSize: 24, lineHeight: 1.2 }}>{selectedProduct.nome}</h3>
                <button className="btn-secondary" onClick={() => setSelectedProduct(null)}>Fechar</button>
              </div>

              <div style={{ fontSize: 26, fontWeight: 800, color: '#c41c1c' }}>
                {formatCurrency(resolveProductPrice(selectedProduct))}
              </div>

              <div style={{ color: '#475569' }}>
                Categoria: <strong>{selectedProduct?.categoria_nome || selectedProduct?.categoria || 'Sem categoria'}</strong>
              </div>
              <div style={{ color: '#475569' }}>
                Estoque disponível: <strong>{Number.isFinite(resolveProductStock(selectedProduct)) ? resolveProductStock(selectedProduct) : 'Disponível'}</strong>
              </div>
              <div style={{ color: '#475569' }}>
                SKU: <strong>{selectedProduct?.codigo || '-'}</strong>
              </div>

              {getProductImages(selectedProduct).length <= 1 && (
                <div style={{ fontSize: 13, color: '#64748b' }}>
                  Este produto ainda não possui galeria com múltiplas fotos cadastradas.
                </div>
              )}

              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                {!isProductOutOfStock(selectedProduct) ? (
                  <button className="btn-primary" onClick={() => addToCart(selectedProduct)} style={{ background: '#c41c1c', border: 'none', color: '#fff', borderRadius: 10, fontWeight: 700, fontSize: 15, padding: '10px 20px', cursor: 'pointer' }}>
                    + Adicionar ao carrinho
                  </button>
                ) : (
                  <button className="btn-secondary" onClick={() => registerNotifyMe(selectedProduct)}>
                    Avise-me quando chegar
                  </button>
                )}
                <button className="btn-secondary" onClick={() => toggleWishlist(selectedProduct.id)}>
                  {wishlist.includes(selectedProduct.id) ? 'Remover da lista' : 'Salvar na lista'}
                </button>
                <button className="btn-secondary" onClick={() => setView('carrinho')}>
                  Ver carrinho
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {view === 'carrinho' && (
        <div style={{ background: '#f8fafc', padding: 16, borderRadius: 14, minHeight: 200 }}>
          <h3 style={{ marginTop: 0, color: '#2e7d32', fontSize: 18 }}>🛒 Carrinho de compras</h3>
          {cartLoading ? (
            <div style={{ textAlign: 'center', color: '#64748b', padding: 20 }}>Carregando carrinho...</div>
          ) : cart?.itens?.length ? (
            <div style={{ display: 'grid', gap: 10 }}>
              {cart.itens.map((item) => {
                const prod = productMap[item.produto_id];
                const img = prod ? getProductImages(prod)[0] : null;
                return (
                  <div key={item.item_id} style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: '12px 14px', display: 'flex', gap: 14, alignItems: 'center', background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
                    <div style={{ width: 80, height: 80, borderRadius: 10, background: '#f8fafc', flexShrink: 0, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e5e7eb' }}>
                      {img ? <img src={img} alt={item.nome} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 4 }} /> : <span style={{ fontSize: 32 }}>📦</span>}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 15, lineHeight: 1.3, marginBottom: 4 }}>{item.nome}</div>
                      <div style={{ fontSize: 13, color: '#c41c1c', fontWeight: 700, marginBottom: 8 }}>{formatCurrency(item.preco_unitario)} / un</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                        <button onClick={() => updateCartItem(item.item_id, item.quantidade - 1)} style={{ background: '#f1f5f9', border: '1px solid #d1d5db', borderRadius: 7, width: 32, height: 32, cursor: 'pointer', fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>−</button>
                        <span style={{ fontWeight: 700, fontSize: 15, minWidth: 28, textAlign: 'center' }}>{item.quantidade}</span>
                        <button onClick={() => updateCartItem(item.item_id, item.quantidade + 1)} style={{ background: '#f1f5f9', border: '1px solid #d1d5db', borderRadius: 7, width: 32, height: 32, cursor: 'pointer', fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>+</button>
                        <button onClick={() => updateCartItem(item.item_id, 0)} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 13, marginLeft: 4, padding: '4px 8px' }}>🗑 Remover</button>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                      <div style={{ fontWeight: 800, fontSize: 16, color: '#111' }}>{formatCurrency(item.preco_unitario * item.quantidade)}</div>
                    </div>
                  </div>
                );
              })}
              <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 2 }}>
                <span style={{ fontWeight: 600, fontSize: 15 }}>Total</span>
                <span style={{ fontWeight: 800, fontSize: 20, color: '#c41c1c' }}>{formatCurrency(cartTotal)}</span>
              </div>
              <button className="btn-primary" onClick={handleCheckoutFromLoja} style={{ background: '#c41c1c', border: 'none', color: '#fff', borderRadius: 12, padding: '14px 0', fontWeight: 800, fontSize: 16, cursor: 'pointer', width: '100%' }}>
                ✅ Finalizar pedido
              </button>
            </div>
          ) : (
            <div style={{ color: '#94a3b8', textAlign: 'center', padding: '32px 0', fontSize: 14 }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>🛒</div>
              <div>Seu carrinho está vazio</div>
              <button className="btn-secondary" onClick={() => setView('loja')} style={{ marginTop: 12 }}>Ver produtos</button>
            </div>
          )}

          <form onSubmit={applyCupom} style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <input
              value={cupom}
              onChange={(e) => setCupom(e.target.value)}
              placeholder="Cupom"
              style={{ flex: 1, padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
            />
            <button className="btn-secondary" type="submit">Aplicar</button>
          </form>

          {cupomResult && (
            <div style={{ marginTop: 8, color: '#0a7d32' }}>
              Cupom {cupomResult.codigo}: -{formatCurrency(cupomResult.desconto)}
            </div>
          )}
        </div>
      )}

      {view === 'checkout' && (
        <div style={{ background: '#fff', padding: 16, borderRadius: 8, display: 'grid', gap: 10 }}>
          <h3 style={{ marginTop: 0 }}>Checkout</h3>
          <form onSubmit={calcularResumoCheckout} style={{ display: 'grid', gap: 8 }}>
            <div style={{ display: 'grid', gap: 6 }}>
              <label style={{ fontSize: 13, color: '#334155' }}>Forma de recebimento</label>
              <div style={{ display: 'flex', gap: 12 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input
                    type="radio"
                    name="deliveryMode"
                    value="entrega"
                    checked={deliveryMode === 'entrega'}
                    onChange={() => setDeliveryMode('entrega')}
                  />
                  Entrega
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input
                    type="radio"
                    name="deliveryMode"
                    value="retirada"
                    checked={deliveryMode === 'retirada'}
                    onChange={() => setDeliveryMode('retirada')}
                  />
                  Retirada na loja
                </label>
              </div>

              {/* Quem vai retirar — só aparece se escolher retirada */}
              {deliveryMode === 'retirada' && (
                <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 12, display: 'grid', gap: 8 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>Quem vai retirar o pedido?</div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="tipoRetirada"
                      value="proprio"
                      checked={tipoRetirada === 'proprio'}
                      onChange={() => setTipoRetirada('proprio')}
                    />
                    <span>🙋 Eu mesmo(a) vou retirar</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="tipoRetirada"
                      value="terceiro"
                      checked={tipoRetirada === 'terceiro'}
                      onChange={() => setTipoRetirada('terceiro')}
                    />
                    <span>� Outra pessoa vai retirar por mim</span>
                  </label>
                  {tipoRetirada === 'terceiro' && (
                    <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 6, padding: 10, fontSize: 12, color: '#92400e' }}>
                      ℹ️ Uma <strong>senha secreta de retirada</strong> será gerada após confirmar o pedido. Compartilhe essa senha com a pessoa que vai retirar.
                    </div>
                  )}
                </div>
              )}
            </div>

            <input
              value={tenantContext?.cidade || cidadeDestino}
              onChange={(e) => setCidadeDestino(e.target.value)}
              placeholder="Cidade da loja"
              disabled={Boolean(tenantContext?.cidade)}
              style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6, background: tenantContext?.cidade ? '#f8fafc' : '#fff' }}
            />

            {deliveryMode === 'entrega' && (
              <>
                <input
                  value={addressFields.cep}
                  onChange={(e) => setAddressFields((prev) => ({ ...prev, cep: e.target.value }))}
                  onBlur={handleCheckoutCepBlur}
                  placeholder="CEP"
                  style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                />
                <input
                  value={addressFields.endereco}
                  onChange={(e) => setAddressFields((prev) => ({ ...prev, endereco: e.target.value }))}
                  placeholder="Rua / Avenida"
                  style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <input
                    value={addressFields.numero}
                    onChange={(e) => setAddressFields((prev) => ({ ...prev, numero: e.target.value }))}
                    placeholder="Número"
                    style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                  />
                  <input
                    value={addressFields.complemento}
                    onChange={(e) => setAddressFields((prev) => ({ ...prev, complemento: e.target.value }))}
                    placeholder="Complemento"
                    style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                  />
                </div>
                <input
                  value={addressFields.bairro}
                  onChange={(e) => setAddressFields((prev) => ({ ...prev, bairro: e.target.value }))}
                  placeholder="Bairro"
                  style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 8 }}>
                  <input
                    value={addressFields.cidade || tenantContext?.cidade || ''}
                    onChange={(e) => setAddressFields((prev) => ({ ...prev, cidade: e.target.value }))}
                    placeholder="Cidade"
                    disabled={Boolean(tenantContext?.cidade)}
                    style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6, background: tenantContext?.cidade ? '#f8fafc' : '#fff' }}
                  />
                  <input
                    value={addressFields.estado || tenantContext?.uf || ''}
                    onChange={(e) => setAddressFields((prev) => ({ ...prev, estado: e.target.value }))}
                    placeholder="UF"
                    style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                  />
                </div>
              </>
            )}
            <button className="btn-secondary" type="submit">Calcular resumo</button>
          </form>

          {checkoutResumo && (
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 10 }}>
              <div>Itens: {checkoutResumo.itens_count}</div>
              <div>Subtotal: {formatCurrency(checkoutResumo.subtotal)}</div>
              <div>Frete: {formatCurrency(checkoutResumo?.frete?.valor_frete)}</div>
              <div>Desconto: {formatCurrency(checkoutResumo?.cupom?.desconto)}</div>
              <div style={{ fontWeight: 700 }}>Total: {formatCurrency(checkoutResumo.total)}</div>
            </div>
          )}

          <button className="btn-primary" onClick={finalizarCheckout} disabled={checkoutLoading || !(tenantContext?.cidade || cidadeDestino) || !cart?.itens?.length || !isProfileComplete}>
            {checkoutLoading ? 'Finalizando...' : 'Finalizar pedido'}
          </button>

          {!isProfileComplete && (
            <div style={{ fontSize: 12, color: '#b45309' }}>
              Complete cadastro (nome completo, telefone, CPF e endereço) na aba Conta para finalizar.
            </div>
          )}

          {checkoutResult?.pedido_id && (
            <div style={{ background: '#e8fff0', color: '#0a7d32', padding: 10, borderRadius: 6, display: 'grid', gap: 6 }}>
              <div>Pedido confirmado: <strong>{checkoutResult.pedido_id}</strong></div>
              {checkoutResult.palavra_chave_retirada && (
                <div style={{ background: '#fff7ed', border: '2px solid #f97316', borderRadius: 8, padding: 12, color: '#7c2d12', textAlign: 'center' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>🔑 SENHA DE RETIRADA</div>
                  <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: 2, color: '#ea580c' }}>{checkoutResult.palavra_chave_retirada}</div>
                  <div style={{ fontSize: 11, marginTop: 6, color: '#92400e' }}>
                    Compartilhe esta senha com a pessoa que vai retirar o pedido na loja.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {view === 'pedidos' && (
        <div style={{ background: '#fff', padding: 16, borderRadius: 8 }}>
          <h3 style={{ marginTop: 0 }}>Meus pedidos</h3>
          {ordersLoading ? (
            <div style={{ color: '#666' }}>Carregando pedidos...</div>
          ) : ordersDetailed.length === 0 ? (
            <div style={{ color: '#666' }}>Nenhum pedido encontrado para esta conta.</div>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {ordersDetailed.map((order) => {
                return (
                  <div key={order.pedido_id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, display: 'grid', gap: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
                      <div>
                        <div style={{ fontWeight: 700 }}>{order.pedido_id}</div>
                        <div style={{ fontSize: 12, color: '#64748b' }}>Origem: {order.origem || '-'}</div>
                      </div>
                      <div style={{ fontWeight: 700 }}>{formatCurrency(order.total)}</div>
                    </div>

                    <div style={{ fontSize: 13 }}>Status do pedido: <strong>{order.status || '-'}</strong></div>
                    <div style={{ fontSize: 13 }}>Data da compra: <strong>{formatDateTime(order.data_compra)}</strong></div>
                    <div style={{ fontSize: 13 }}>
                      Data do pagamento: <strong>{order.data_pagamento ? formatDateTime(order.data_pagamento) : 'Aguardando pagamento'}</strong>
                    </div>

                    {/* Senha de retirada por terceiro */}
                    {order.palavra_chave_retirada && (
                      <div style={{ background: '#fff7ed', border: '2px solid #f97316', borderRadius: 8, padding: 12, textAlign: 'center' }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: '#7c2d12', marginBottom: 4 }}>🔑 SENHA DE RETIRADA</div>
                        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: 2, color: '#ea580c' }}>{order.palavra_chave_retirada}</div>
                        <div style={{ fontSize: 11, color: '#92400e', marginTop: 4 }}>Apresente esta senha na loja para retirar o pedido</div>
                      </div>
                    )}

                    <div style={{ fontSize: 13, fontWeight: 700, marginTop: 2 }}>Produtos do pedido ({order.itens_count || 0})</div>
                    {Array.isArray(order.itens) && order.itens.length > 0 ? (
                      <div style={{ display: 'grid', gap: 6 }}>
                        {order.itens.map((item, index) => (
                          <div key={`${order.pedido_id}-${item.produto_id || index}`} style={{ border: '1px solid #f1f5f9', borderRadius: 6, padding: 8 }}>
                            <div style={{ fontSize: 13, fontWeight: 600 }}>{item.nome || 'Produto'}</div>
                            <div style={{ fontSize: 12, color: '#475569' }}>
                              {item.quantidade} x {formatCurrency(item.preco_unitario)} = {formatCurrency(item.subtotal)}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: 12, color: '#666' }}>Sem itens detalhados para este pedido.</div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <button className="btn-secondary" onClick={loadOrdersDetailed} style={{ marginTop: 10 }} disabled={ordersLoading}>
            {ordersLoading ? 'Atualizando...' : 'Atualizar pedidos'}
          </button>
        </div>
      )}

      {view === 'conta' && (
        <>
          {customerToken ? (
            <div style={{ background: '#fff', padding: 16, borderRadius: 8, display: 'grid', gap: 10 }}>
              <h3 style={{ marginTop: 0, marginBottom: 0 }}>Meus dados cadastrais</h3>
              <div style={{ fontSize: 13, color: '#64748b' }}>
                Esses dados ficam vinculados à sua conta e serão usados no pedido e no PDV.
              </div>

              <form onSubmit={saveProfile} style={{ display: 'grid', gap: 8 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <input value={profileForm.nome} onChange={(e) => setProfileForm((prev) => ({ ...prev, nome: e.target.value }))} placeholder="Nome completo" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                  <input value={customer?.email || ''} disabled placeholder="Email" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6, background: '#f8fafc' }} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <input value={profileForm.telefone} onChange={(e) => setProfileForm((prev) => ({ ...prev, telefone: e.target.value }))} placeholder="Telefone" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                  <input value={profileForm.cpf} onChange={(e) => setProfileForm((prev) => ({ ...prev, cpf: e.target.value }))} placeholder="CPF" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                </div>

                <input
                  value={profileForm.cep}
                  onChange={(e) => setProfileForm((prev) => ({ ...prev, cep: e.target.value }))}
                  onBlur={handleProfileCepBlur}
                  placeholder="CEP"
                  style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                />

                <input value={profileForm.endereco} onChange={(e) => setProfileForm((prev) => ({ ...prev, endereco: e.target.value }))} placeholder="Endereço" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />

                <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 8 }}>
                  <input value={profileForm.numero} onChange={(e) => setProfileForm((prev) => ({ ...prev, numero: e.target.value }))} placeholder="Número" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                  <input value={profileForm.complemento} onChange={(e) => setProfileForm((prev) => ({ ...prev, complemento: e.target.value }))} placeholder="Complemento" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 120px', gap: 8 }}>
                  <input value={profileForm.bairro} onChange={(e) => setProfileForm((prev) => ({ ...prev, bairro: e.target.value }))} placeholder="Bairro" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                  <input value={profileForm.cidade} onChange={(e) => setProfileForm((prev) => ({ ...prev, cidade: e.target.value }))} placeholder="Cidade" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                  <input value={profileForm.estado} onChange={(e) => setProfileForm((prev) => ({ ...prev, estado: e.target.value }))} placeholder="UF" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                </div>

                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() =>
                    setProfileForm((prev) => ({
                      ...prev,
                      usar_endereco_entrega_diferente: !prev.usar_endereco_entrega_diferente,
                    }))
                  }
                  style={{ justifySelf: 'start' }}
                >
                  {profileForm.usar_endereco_entrega_diferente ? 'Remover endereço de entrega diferente' : 'Usar endereço de entrega diferente'}
                </button>

                {profileForm.usar_endereco_entrega_diferente && (
                  <div style={{ display: 'grid', gap: 8, border: '1px solid #e5e7eb', borderRadius: 8, padding: 10, background: '#f8fafc' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>Endereço de entrega (dados complementares)</div>
                    <input
                      value={profileForm.entrega_nome}
                      onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_nome: e.target.value }))}
                      placeholder="Nome completo para entrega"
                      style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                    />
                    <input
                      value={profileForm.entrega_cep}
                      onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_cep: e.target.value }))}
                      onBlur={handleDeliveryCepBlur}
                      placeholder="CEP"
                      style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                    />
                    <input
                      value={profileForm.entrega_endereco}
                      onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_endereco: e.target.value }))}
                      placeholder="Rua / Avenida"
                      style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 8 }}>
                      <input
                        value={profileForm.entrega_numero}
                        onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_numero: e.target.value }))}
                        placeholder="Número"
                        style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                      />
                      <input
                        value={profileForm.entrega_complemento}
                        onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_complemento: e.target.value }))}
                        placeholder="Complemento"
                        style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                      />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 120px', gap: 8 }}>
                      <input
                        value={profileForm.entrega_bairro}
                        onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_bairro: e.target.value }))}
                        placeholder="Bairro"
                        style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                      />
                      <input
                        value={profileForm.entrega_cidade}
                        onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_cidade: e.target.value }))}
                        placeholder="Cidade"
                        style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                      />
                      <input
                        value={profileForm.entrega_estado}
                        onChange={(e) => setProfileForm((prev) => ({ ...prev, entrega_estado: e.target.value }))}
                        placeholder="UF"
                        style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }}
                      />
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button className="btn-primary" type="submit" disabled={profileSaving}>
                    {profileSaving ? 'Salvando...' : 'Salvar cadastro'}
                  </button>
                  <button className="btn-secondary" type="button" onClick={logoutCustomer}>Sair</button>
                </div>
              </form>

              <div style={{ fontSize: 12, color: '#64748b' }}>
                Lista de desejos: {wishlist.length} item(ns) • Avise-me: {notifyRequests.length} solicitação(ões)
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div style={{ background: '#fff', padding: 16, borderRadius: 8 }}>
                <h3 style={{ marginTop: 0 }}>Cadastro</h3>
                <form onSubmit={handleRegister} autoComplete="off" style={{ display: 'grid', gap: 8 }}>
                  <input name="ecommerce_register_nome" autoComplete="off" value={registerForm.nome} onChange={(e) => setRegisterForm((prev) => ({ ...prev, nome: e.target.value }))} placeholder="Nome completo" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                  <input name="ecommerce_register_email" autoComplete="off" value={registerForm.email} onChange={(e) => setRegisterForm((prev) => ({ ...prev, email: e.target.value }))} placeholder="Email" type="email" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                    <input name="ecommerce_register_password" autoComplete="new-password" value={registerForm.password} onChange={(e) => setRegisterForm((prev) => ({ ...prev, password: e.target.value }))} placeholder="Senha" type={showRegisterPassword ? 'text' : 'password'} style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                    <button className="btn-secondary" type="button" onClick={() => setShowRegisterPassword((prev) => !prev)}>
                      {showRegisterPassword ? 'Ocultar' : '👁 Mostrar'}
                    </button>
                  </div>
                  <button className="btn-primary" type="submit" disabled={authLoading}>Cadastrar</button>
                </form>
              </div>

              <div style={{ background: '#fff', padding: 16, borderRadius: 8 }}>
                <h3 style={{ marginTop: 0 }}>Login</h3>
                <form onSubmit={handleLogin} autoComplete="off" style={{ display: 'grid', gap: 8 }}>
                  <input name="ecommerce_login_email" autoComplete="off" value={loginForm.email} onChange={(e) => setLoginForm((prev) => ({ ...prev, email: e.target.value }))} placeholder="Email" type="email" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                    <input name="ecommerce_login_password" autoComplete="new-password" value={loginForm.password} onChange={(e) => setLoginForm((prev) => ({ ...prev, password: e.target.value }))} placeholder="Senha" type={showLoginPassword ? 'text' : 'password'} style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6 }} />
                    <button className="btn-secondary" type="button" onClick={() => setShowLoginPassword((prev) => !prev)}>
                      {showLoginPassword ? 'Ocultar' : '👁 Mostrar'}
                    </button>
                  </div>
                  <button className="btn-primary" type="submit" disabled={authLoading}>Entrar</button>
                </form>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
