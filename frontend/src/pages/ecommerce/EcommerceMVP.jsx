import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import ecommerceApi from '../../services/ecommerceApi';
import { api } from '../../services/api';
import EcommerceAccountPage from './EcommerceAccountPage';
import EcommerceCatalogControls, { EcommerceCatalogSummary } from './EcommerceCatalogControls';
import EcommerceCatalogProductCard from './EcommerceCatalogProductCard';
import { EcommerceCartPage, EcommerceCartSidebar } from './EcommerceCartPanels';
import EcommerceCheckoutPage from './EcommerceCheckoutPage';
import EcommerceOrdersPage from './EcommerceOrdersPage';
import EcommerceProductDetailModal from './EcommerceProductDetailModal';
import EcommerceStorefrontShell from './EcommerceStorefrontShell';
import { ecommerceMvpStyles as S } from './ecommerceMvpStyles';
import {
  trackPageView,
  trackViewItem,
  trackAddToCart,
  trackBeginCheckout,
  trackPurchase,
  trackViewCart,
} from '../../services/analytics';
import {
  BANNERS,
  EMPTY_CART,
  STORAGE_ADDRESS_KEY,
  STORAGE_GUEST_CART_KEY,
  STORAGE_NOTIFY_KEY,
  STORAGE_ORDERS_KEY,
  STORAGE_TOKEN_KEY,
  STORAGE_WISHLIST_KEY,
  buildAddressText,
  buildIdempotencyKey,
  extractApiErrorMessage,
  fetchAddressByCep,
  getGuestCart,
  getProductImages,
  getStoredAddressFields,
  humanizeSlug,
  isLikelyCorruptedText,
  isProductOutOfStock,
  normalizeProductPayload,
  recalculateGuestCart,
  resolveProductPrice,
  resolveProductStock,
  resolveValidityPromotionLimit,
} from './ecommerceMvpUtils';

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

  // Detecta mobile (< 768px)
  const [isMobile, setIsMobile] = useState(typeof window !== 'undefined' ? window.innerWidth < 768 : false);
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

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
  const [somenteComEstoque, setSomenteComEstoque] = useState(false);
  const [somenteComImagem, setSomenteComImagem] = useState(false);
  const [ordenacaoCatalogo, setOrdenacaoCatalogo] = useState('prontos');
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRecoveryPassword, setShowRecoveryPassword] = useState(false);
  const [showRecoveryConfirmPassword, setShowRecoveryConfirmPassword] = useState(false);

  const [authLoading, setAuthLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [cartLoading, setCartLoading] = useState(false);
  const [recoveryLoading, setRecoveryLoading] = useState(false);

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

  const [registerForm, setRegisterForm] = useState({
    email: '',
    password: '',
    nome: '',
    cpf: '',
    telefone: '',
    accepted_terms: false,
    accepted_privacy: false,
  });
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [passwordRecoveryMode, setPasswordRecoveryMode] = useState(false);
  const [recoveryStep, setRecoveryStep] = useState('request');
  const [recoveryTokenFromLink, setRecoveryTokenFromLink] = useState(false);
  const [recoveryForm, setRecoveryForm] = useState({
    email: '',
    token: '',
    novaSenha: '',
    confirmarSenha: '',
  });

  const [cart, setCart] = useState(() => getGuestCart());
  const [cupom, setCupom] = useState('');
  const [cupomResult, setCupomResult] = useState(null);

  const [cidadeDestino, setCidadeDestino] = useState('');
  const [deliveryMode, setDeliveryMode] = useState('entrega');
  const [tipoRetirada, setTipoRetirada] = useState('proprio'); // 'proprio' | 'terceiro'
  const [isDrive, setIsDrive] = useState(false); // cliente quer drive pickup
  const [addressFields, setAddressFields] = useState(() => getStoredAddressFields());
  const [checkoutResumo, setCheckoutResumo] = useState(null);
  const [checkoutResult, setCheckoutResult] = useState(null);
  const [pagamentoTipo, setPagamentoTipo] = useState(''); // 'pix'|'debito'|'credito'
  const [pagamentoBandeira, setPagamentoBandeira] = useState('Visa');
  const [pagamentoParcelas, setPagamentoParcelas] = useState(1);
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

  const catalogMetrics = useMemo(() => {
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
  }, [products]);

  const filteredProducts = useMemo(() => {
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
  }, [products, search, categoria, somenteComEstoque, somenteComImagem, ordenacaoCatalogo]);

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
    const params = new URLSearchParams(location.search);
    const recoveryFlag = params.get('recovery');
    const emailParam = params.get('email') || '';
    const tokenParam = params.get('token') || '';

    if (recoveryFlag !== '1' && !emailParam && !tokenParam) {
      return;
    }

    setView('conta');
    setPasswordRecoveryMode(true);
    setRecoveryStep(tokenParam ? 'reset' : 'request');
    setRecoveryTokenFromLink(Boolean(tokenParam));
    setRecoveryForm((prev) => ({
      ...prev,
      email: emailParam || prev.email,
      token: tokenParam || prev.token,
    }));
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
        params: { tenant: tenantRef, limit: 500, ordenacao: 'prontos' },
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
        params: { tenant: tenantId, limit: 500, ordenacao: 'prontos' },
      });
      setProducts(normalizeProductPayload(response?.data));
    } catch (err) {
      setProducts([]);
      setError(extractApiErrorMessage(err, 'Erro ao carregar produtos vendáveis'));
    } finally {
      setLoading(false);
    }
  }

  function clearCatalogFilters() {
    setSearch('');
    setCategoria('todas');
    setSomenteComEstoque(false);
    setSomenteComImagem(false);
    setOrdenacaoCatalogo('prontos');
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

    const phoneDigits = String(profileForm.telefone || '').replace(/\D/g, '');
    if (phoneDigits.length < 10) {
      setError('Informe um telefone/celular valido.');
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

  function clearRecoveryParamsFromUrl() {
    const params = new URLSearchParams(location.search);
    params.delete('recovery');
    params.delete('email');
    params.delete('token');
    const nextSearch = params.toString();
    navigate(`${location.pathname}${nextSearch ? `?${nextSearch}` : ''}`, { replace: true });
  }

  function openPasswordRecovery(nextStep = 'request') {
    setView('conta');
    setPasswordRecoveryMode(true);
    setRecoveryStep(nextStep);
    setRecoveryTokenFromLink(false);
    setError('');
    setSuccess('');
    setRecoveryForm((prev) => ({
      ...prev,
      email: prev.email || loginForm.email || registerForm.email || customer?.email || '',
      token: nextStep === 'request' ? '' : prev.token,
      novaSenha: '',
      confirmarSenha: '',
    }));
  }

  function closePasswordRecovery() {
    setPasswordRecoveryMode(false);
    setRecoveryStep('request');
    setRecoveryTokenFromLink(false);
    setShowRecoveryPassword(false);
    setShowRecoveryConfirmPassword(false);
    setRecoveryForm((prev) => ({
      ...prev,
      token: '',
      novaSenha: '',
      confirmarSenha: '',
    }));
    clearRecoveryParamsFromUrl();
  }

  async function handlePasswordRecoveryRequest(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      setError('Loja não identificada na URL.');
      return;
    }

    const normalizedEmail = recoveryForm.email.trim().toLowerCase();
    if (!normalizedEmail) {
      setError('Informe o e-mail da conta para continuar.');
      return;
    }

    setRecoveryLoading(true);
    setError('');
    setSuccess('');
    try {
      const response = await ecommerceApi.post(
        '/api/ecommerce/auth/esqueci-senha',
        { email: normalizedEmail, canal: 'site' },
        { headers: tenantHeaders }
      );
      const minutes = response?.data?.expires_in_minutes;
      setRecoveryStep('request');
      setRecoveryForm((prev) => ({
        ...prev,
        email: normalizedEmail,
        token: '',
        novaSenha: '',
        confirmarSenha: '',
      }));
      setRecoveryTokenFromLink(false);
      setSuccess(
        minutes
          ? `Se o e-mail existir, enviamos um link e um codigo de recuperacao. Abra o ultimo e-mail recebido ou clique em "Ja tenho o codigo". Eles expiram em ${minutes} minutos.`
          : 'Se o e-mail existir, enviamos as instruções de recuperação.'
      );
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Não foi possível iniciar a recuperação agora.'));
    } finally {
      setRecoveryLoading(false);
    }
  }

  async function handlePasswordRecoveryReset(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      setError('Loja não identificada na URL.');
      return;
    }

    const normalizedEmail = recoveryForm.email.trim().toLowerCase();
    const token = recoveryForm.token.trim();

    if (!normalizedEmail || !token) {
      setError(recoveryTokenFromLink ? 'Link de recuperacao invalido. Solicite um novo link.' : 'Preencha o e-mail e o codigo recebido.');
      return;
    }

    if ((recoveryForm.novaSenha || '').length < 8) {
      setError('A nova senha deve ter pelo menos 8 caracteres.');
      return;
    }

    if (recoveryForm.novaSenha !== recoveryForm.confirmarSenha) {
      setError('A confirmação da senha não confere.');
      return;
    }

    setRecoveryLoading(true);
    setError('');
    setSuccess('');
    try {
      await ecommerceApi.post(
        '/api/ecommerce/auth/resetar-senha',
        {
          email: normalizedEmail,
          token,
          nova_senha: recoveryForm.novaSenha,
        },
        { headers: tenantHeaders }
      );
      setLoginForm({ email: normalizedEmail, password: '' });
      setRecoveryForm({
        email: normalizedEmail,
        token: '',
        novaSenha: '',
        confirmarSenha: '',
      });
      setPasswordRecoveryMode(false);
      setRecoveryStep('request');
      setRecoveryTokenFromLink(false);
      setShowRecoveryPassword(false);
      setShowRecoveryConfirmPassword(false);
      clearRecoveryParamsFromUrl();
      setSuccess('Senha atualizada com sucesso. Agora é só entrar com a nova senha.');
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Não foi possível redefinir a senha.'));
    } finally {
      setRecoveryLoading(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    if (!tenantContext?.id) {
      setError('Loja não identificada na URL.');
      return;
    }
    const cpfDigits = (registerForm.cpf || '').replace(/\D/g, '');
    if (cpfDigits.length !== 11) {
      setError('Informe um CPF válido com 11 dígitos.');
      return;
    }
    const phoneDigits = (registerForm.telefone || '').replace(/\D/g, '');
    if (phoneDigits.length < 10) {
      setError('Informe um telefone/celular valido.');
      return;
    }
    if ((registerForm.password || '').length < 8) {
      setError('A senha deve ter pelo menos 8 caracteres.');
      return;
    }
    if (!registerForm.accepted_terms || !registerForm.accepted_privacy) {
      setError('Aceite os Termos de Uso e a Politica de Privacidade para criar a conta.');
      return;
    }
    setAuthLoading(true);
    setError('');
    setSuccess('');
    try {
      const response = await ecommerceApi.post('/api/ecommerce/auth/registrar', registerForm, { headers: tenantHeaders });
      if (response?.data?.requires_email_verification) {
        setRegisterForm({
          email: '',
          password: '',
          nome: '',
          cpf: '',
          telefone: '',
          accepted_terms: false,
          accepted_privacy: false,
        });
        setPasswordRecoveryMode(false);
        setRecoveryStep('request');
        clearRecoveryParamsFromUrl();
        setSuccess('Cadastro realizado. Enviamos um link de confirmacao para o seu e-mail antes do primeiro acesso.');
        return;
      }
      const token = response?.data?.access_token;
      if (!token) throw new Error('Token não retornado');
      if (response?.data?.user) {
        setCustomer(response.data.user);
      }
      localStorage.setItem(STORAGE_TOKEN_KEY, token);
      setCustomerToken(token);
      await syncGuestCartToServer(token);
      setRegisterForm({
        email: '',
        password: '',
        nome: '',
        cpf: '',
        telefone: '',
        accepted_terms: false,
        accepted_privacy: false,
      });
      setPasswordRecoveryMode(false);
      setRecoveryStep('request');
      clearRecoveryParamsFromUrl();
      setSuccess('Cadastro realizado com sucesso!');
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
      setPasswordRecoveryMode(false);
      setRecoveryStep('request');
      clearRecoveryParamsFromUrl();
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
      const limiteValidade = resolveValidityPromotionLimit(product);
      const quantidadeAtual = Array.isArray(cart?.itens)
        ? Number(cart.itens.find((item) => item.produto_id === product.id)?.quantidade || 0)
        : 0;
      if (limiteValidade && quantidadeAtual + 1 > limiteValidade) {
        setError(`Oferta de validade disponivel para ate ${limiteValidade} unidade(s) nesse preco.`);
        return;
      }
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
      const itemAtual = Array.isArray(cart?.itens)
        ? cart.itens.find((item) => item.item_id === itemId)
        : null;
      const produtoAtual = itemAtual ? productMap[itemAtual.produto_id] : null;
      const limiteValidade = resolveValidityPromotionLimit(produtoAtual);
      if (limiteValidade && quantidade > limiteValidade) {
        setError(`Oferta de validade disponivel para ate ${limiteValidade} unidade(s) nesse preco.`);
        return;
      }
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
    if (!pagamentoTipo) {
      setError('Escolha PIX, debito ou credito para continuar para o pagamento.');
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
          is_drive: deliveryMode === 'retirada' && tipoRetirada === 'proprio' ? isDrive : false,
          forma_pagamento_nome: (() => {
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

      setSuccess('Pagamento enviado para analise. O pedido sera liberado apos aprovacao.');
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

  async function avisarCheguei(pedidoId) {
    try {
      await ecommerceApi.post(`/api/checkout/pedido/${pedidoId}/drive-cheguei`, {}, { headers: authHeaders });
      await loadOrdersDetailed();
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao avisar chegada'));
    }
  }

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

  return (
    <EcommerceStorefrontShell
      activeBanners={activeBanners}
      bannerSlide={bannerSlide}
      cart={cart}
      cartTotal={cartTotal}
      customerDisplayName={customerDisplayName}
      error={error}
      isMobile={isMobile}
      notifyMeModal={notifyMeModal}
      search={search}
      storeDisplayName={storeDisplayName}
      styles={S}
      success={success}
      tenantContext={tenantContext}
      tenantRef={tenantRef}
      view={view}
      wishlistCount={wishlist.length}
      onBannerSlideChange={setBannerSlide}
      onNotifyMeClose={() => setNotifyMeModal({ open: false, product: null, email: '', loading: false })}
      onNotifyMeEmailChange={(email) => setNotifyMeModal((prev) => ({ ...prev, email }))}
      onNotifyMeSubmit={submitNotifyMe}
      onSearchChange={setSearch}
      onViewChange={setView}
    >

      {view === 'loja' && (
        <>
          <EcommerceCatalogSummary
            catalogMetrics={catalogMetrics}
            isMobile={isMobile}
            productCount={filteredProducts.length}
          />

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'minmax(0, 1fr) 300px', gap: 24, maxWidth: 1280, margin: '0 auto', padding: isMobile ? '12px 12px 28px' : '16px 20px 28px' }}>
            {/* PRODUTOS */}
            <div>
              <EcommerceCatalogControls
                categories={categorias}
                category={categoria}
                isMobile={isMobile}
                loading={loading}
                order={ordenacaoCatalogo}
                search={search}
                showOnlyInStock={somenteComEstoque}
                showOnlyWithImage={somenteComImagem}
                styles={S}
                onCategoryChange={setCategoria}
                onClearFilters={clearCatalogFilters}
                onImageFilterChange={() => setSomenteComImagem((value) => !value)}
                onOrderChange={setOrdenacaoCatalogo}
                onRefresh={loadProducts}
                onSearchChange={setSearch}
                onStockFilterChange={() => setSomenteComEstoque((value) => !value)}
              />

              {/* Grid */}
              <div style={{ ...S.grid, gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(auto-fill, minmax(200px, 1fr))', gap: isMobile ? 10 : 16 }}>
                {filteredProducts.map((product) => (
                  <EcommerceCatalogProductCard
                    key={product.id}
                    product={product}
                    isHovered={hoveredCard === product.id}
                    wished={wishlist.includes(product.id)}
                    styles={S}
                    onAddToCart={addToCart}
                    onHover={setHoveredCard}
                    onNotifyMe={registerNotifyMe}
                    onOpen={openProductDetails}
                    onToggleWishlist={toggleWishlist}
                  />
                ))}
                {!loading && filteredProducts.length === 0 && (
                  <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '60px 0', color: '#9ca3af' }}>
                    <div style={{ fontSize: 48, marginBottom: 12 }}>🔍</div>
                    <div style={{ fontWeight: 800, fontSize: 18, color: '#374151' }}>Nenhum produto encontrado</div>
                    <div style={{ fontSize: 13, marginTop: 4 }}>Tente buscar por outro termo ou categoria</div>
                    <button onClick={clearCatalogFilters} style={{ marginTop: 16, padding: '8px 20px', borderRadius: 20, border: '1.5px solid #e7e5e4', background: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600, color: '#f97316' }}>
                      Limpar filtros
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* SIDEBAR CARRINHO */}
            <EcommerceCartSidebar
              cart={cart}
              cartTotal={cartTotal}
              customerToken={customerToken}
              isMobile={isMobile}
              productMap={productMap}
              styles={S}
              onCheckout={handleCheckoutFromLoja}
              onViewCart={() => setView('carrinho')}
            />
        </div>
        </>
      )}

      {selectedProduct && (
        <EcommerceProductDetailModal
          activeImage={activeProductImage}
          isMobile={isMobile}
          product={selectedProduct}
          styles={S}
          wishlist={wishlist}
          onAddToCart={addToCart}
          onClose={closeProductModal}
          onCopyLink={(product) => {
            const url = `${window.location.origin}${location.pathname}?produto=${product.id}`;
            navigator.clipboard?.writeText(url).then(() => setSuccess('Link copiado!')).catch(() => setSuccess(`Link: ${url}`));
          }}
          onImageChange={setActiveProductImage}
          onNotifyMe={registerNotifyMe}
          onToggleWishlist={toggleWishlist}
          onViewCart={() => {
            closeProductModal();
            setView('carrinho');
          }}
        />
      )}

      {view === 'carrinho' && (
        <EcommerceCartPage
          cart={cart}
          cartLoading={cartLoading}
          cartTotal={cartTotal}
          cupom={cupom}
          cupomResult={cupomResult}
          productMap={productMap}
          styles={S}
          onApplyCoupon={applyCupom}
          onCheckout={handleCheckoutFromLoja}
          onContinueShopping={() => setView('loja')}
          onCouponChange={setCupom}
          onUpdateItem={updateCartItem}
        />
      )}

      {view === 'checkout' && (
        <EcommerceCheckoutPage
          addressFields={addressFields}
          cart={cart}
          cartTotal={cartTotal}
          checkoutLoading={checkoutLoading}
          checkoutResult={checkoutResult}
          checkoutResumo={checkoutResumo}
          cidadeDestino={cidadeDestino}
          deliveryMode={deliveryMode}
          isDrive={isDrive}
          isProfileComplete={isProfileComplete}
          pagamentoBandeira={pagamentoBandeira}
          pagamentoParcelas={pagamentoParcelas}
          pagamentoTipo={pagamentoTipo}
          tenantContext={tenantContext}
          tipoRetirada={tipoRetirada}
          styles={S}
          onAddressFieldsChange={setAddressFields}
          onCalculateSummary={calcularResumoCheckout}
          onCheckoutCepBlur={handleCheckoutCepBlur}
          onCityChange={setCidadeDestino}
          onDeliveryModeChange={setDeliveryMode}
          onDriveChange={setIsDrive}
          onFinalizeCheckout={finalizarCheckout}
          onPaymentBrandChange={setPagamentoBandeira}
          onPaymentInstallmentsChange={setPagamentoParcelas}
          onPaymentTypeChange={setPagamentoTipo}
          onPickupTypeChange={setTipoRetirada}
        />
      )}

      {view === 'pedidos' && (
        <EcommerceOrdersPage
          ordersDetailed={ordersDetailed}
          ordersLoading={ordersLoading}
          styles={S}
          onContinueShopping={() => setView('loja')}
          onDriveArrived={avisarCheguei}
          onRefresh={loadOrdersDetailed}
        />
      )}
      {view === 'conta' && (
        <EcommerceAccountPage
          authLoading={authLoading}
          customer={customer}
          customerToken={customerToken}
          isMobile={isMobile}
          loginForm={loginForm}
          notifyRequestsCount={notifyRequests.length}
          passwordRecoveryMode={passwordRecoveryMode}
          profileForm={profileForm}
          profileSaving={profileSaving}
          recoveryForm={recoveryForm}
          recoveryLoading={recoveryLoading}
          recoveryStep={recoveryStep}
          recoveryTokenFromLink={recoveryTokenFromLink}
          registerForm={registerForm}
          showLoginPassword={showLoginPassword}
          showRecoveryConfirmPassword={showRecoveryConfirmPassword}
          showRecoveryPassword={showRecoveryPassword}
          showRegisterPassword={showRegisterPassword}
          styles={S}
          wishlistCount={wishlist.length}
          onClosePasswordRecovery={closePasswordRecovery}
          onDeliveryCepBlur={handleDeliveryCepBlur}
          onLogin={handleLogin}
          onLoginFormChange={setLoginForm}
          onLogout={logoutCustomer}
          onOpenPasswordRecovery={openPasswordRecovery}
          onPasswordRecoveryRequest={handlePasswordRecoveryRequest}
          onPasswordRecoveryReset={handlePasswordRecoveryReset}
          onProfileCepBlur={handleProfileCepBlur}
          onProfileFormChange={setProfileForm}
          onRegister={handleRegister}
          onRegisterFormChange={setRegisterForm}
          onRecoveryFormChange={setRecoveryForm}
          onRequestNewRecoveryLink={() => {
            setRecoveryStep('request');
            setRecoveryTokenFromLink(false);
            setError('');
            setSuccess('');
          }}
          onSaveProfile={saveProfile}
          onToggleLoginPassword={() => setShowLoginPassword((prev) => !prev)}
          onToggleRecoveryConfirmPassword={() => setShowRecoveryConfirmPassword((prev) => !prev)}
          onToggleRecoveryPassword={() => setShowRecoveryPassword((prev) => !prev)}
          onToggleRegisterPassword={() => setShowRegisterPassword((prev) => !prev)}
          onUseRecoveryCode={() => {
            setRecoveryStep('reset');
            setRecoveryTokenFromLink(false);
          }}
        />
      )}

    </EcommerceStorefrontShell>
  );
}
