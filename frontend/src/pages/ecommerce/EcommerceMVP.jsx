import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import ecommerceApi from '../../services/ecommerceApi';
import { api } from '../../services/api';
import EcommerceCatalogControls, { EcommerceCatalogSummary } from './EcommerceCatalogControls';
import EcommerceCatalogProductCard from './EcommerceCatalogProductCard';
import { EcommerceCartPage, EcommerceCartSidebar } from './EcommerceCartPanels';
import EcommerceProductDetailModal from './EcommerceProductDetailModal';
import {
  trackPageView,
  trackViewItem,
  trackAddToCart,
  trackBeginCheckout,
  trackPurchase,
  trackViewCart,
} from '../../services/analytics';
import {
  EMPTY_CART,
  STORAGE_ADDRESS_KEY,
  STORAGE_GUEST_CART_KEY,
  STORAGE_NOTIFY_KEY,
  STORAGE_ORDERS_KEY,
  STORAGE_TOKEN_KEY,
  STORAGE_WISHLIST_KEY,
  buildActiveBanners,
  buildCatalogCategories,
  buildCustomerAddressFields,
  buildCustomerProfileForm,
  buildAddressText,
  buildIdempotencyKey,
  buildProductMap,
  calculateCatalogMetrics,
  extractApiErrorMessage,
  fetchAddressByCep,
  filterCatalogProducts,
  formatCurrency,
  formatDateTime,
  getGuestCart,
  getProductImages,
  getStoredAddressFields,
  isCustomerProfileComplete,
  isProductOutOfStock,
  normalizeProductPayload,
  recalculateGuestCart,
  resolveMediaUrl,
  resolveProductPrice,
  resolveProductStock,
  resolveStoreDisplayName,
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
    return buildActiveBanners(tenantContext);
  }, [tenantContext]);

  const isProfileComplete = useMemo(() => {
    return isCustomerProfileComplete(customer);
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
    return buildCatalogCategories(products);
  }, [products]);

  const catalogMetrics = useMemo(() => {
    return calculateCatalogMetrics(products);
  }, [products]);

  const filteredProducts = useMemo(() => {
    return filterCatalogProducts(products, {
      search,
      categoria,
      somenteComEstoque,
      somenteComImagem,
      ordenacaoCatalogo,
    });
  }, [products, search, categoria, somenteComEstoque, somenteComImagem, ordenacaoCatalogo]);

  const productMap = useMemo(() => buildProductMap(products), [products]);
  const storefrontRef = tenantContext?.ecommerce_slug || tenantRef || '';
  const customerDisplayName = customer?.nome || customer?.email || '';

  const storeDisplayName = useMemo(() => {
    return resolveStoreDisplayName({ tenantContext, storefrontRef });
  }, [tenantContext, storefrontRef]);

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
    setProfileForm(buildCustomerProfileForm(customer));
  }, [customer]);

  useEffect(() => {
    if (!customer) return;
    setAddressFields(buildCustomerAddressFields(customer));
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

  /* ─────────────── ESTILOS INTERNOS ─────────────── */
  const S = {
    page: { minHeight: '100vh', background: '#faf7f4', fontFamily: "'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif" },
    /* Topbar */
    topbar: { background: 'linear-gradient(90deg,#f97316 0%,#fb923c 100%)', color: '#fff', padding: '6px 20px', fontSize: 11, fontWeight: 500, position: 'sticky', top: 0, zIndex: 50 },
    topbarInner: { maxWidth: 1280, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
    header: { background: '#fff', borderBottom: '1px solid #e7e5e4', padding: '12px 20px', position: 'sticky', top: 32, zIndex: 40, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
    headerInner: { maxWidth: 1280, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 },
    logo: { fontSize: 20, fontWeight: 800, color: '#1c1917', display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' },
    cityChip: { fontSize: 11, color: '#a8a29e', borderLeft: '1px solid #e7e5e4', paddingLeft: 12, fontWeight: 400 },
    headerActions: { display: 'flex', gap: 10, alignItems: 'center' },
    avatarBtn: { background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 24, padding: '7px 14px', fontSize: 13, fontWeight: 600, color: '#ea580c', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' },
    loginBtn: { background: '#fff', border: '1.5px solid #d1d5db', color: '#374151', borderRadius: 24, padding: '7px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 },
    cartBtn: { background: '#f97316', color: '#fff', border: 'none', borderRadius: 12, height: 42, padding: '0 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7, position: 'relative', flexShrink: 0, fontWeight: 700, fontSize: 14 },
    headerWishBtn: { background: 'transparent', border: 'none', color: '#78716c', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 38, height: 38, borderRadius: '50%', transition: 'color 0.15s' },
    cartBadge: { position: 'absolute', top: -5, right: -5, background: '#10b981', color: '#fff', borderRadius: 20, minWidth: 18, height: 18, fontSize: 10, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #fff', padding: '0 3px' },
    /* Floating cart bar */
    floatBar: { position: 'sticky', top: 0, zIndex: 45, background: '#ea580c', color: '#fff', padding: '10px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' },
    /* Nav tabs */
    navWrap: { background: 'transparent', borderBottom: '1px solid #e7e5e4' },
    navInner: { maxWidth: 1280, margin: '0 auto', display: 'flex', padding: '0 20px' },
    navTab: (active) => ({ flex: '0 0 auto', background: 'transparent', border: 'none', borderBottom: active ? '2px solid #f97316' : '2px solid transparent', color: active ? '#f97316' : '#78716c', padding: '13px 18px', fontWeight: active ? 700 : 500, fontSize: 14, cursor: 'pointer', transition: 'all 0.15s', marginBottom: -1 }),
    /* Banner */
    bannerWrap: { position: 'relative', overflow: 'hidden', height: 260, background: '#1c1917' },
    appBar: { padding: '8px 20px 0' },
    appBarInner: { maxWidth: 1280, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: '#166534', background: '#dcfce7', border: '1px solid #bbf7d0', borderRadius: 10, padding: '10px 16px' },
    bannerDots: { position: 'absolute', bottom: 14, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 6 },
    bannerDot: (active) => ({ width: active ? 26 : 9, height: 9, background: active ? '#fff' : 'rgba(255,255,255,0.4)', borderRadius: 5, border: 'none', cursor: 'pointer', padding: 0, transition: 'all 0.3s' }),
    /* Alert messages */
    alertError: { background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca', borderRadius: 10, padding: '10px 14px', fontSize: 13, margin: '10px 0' },
    alertSuccess: { background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0', borderRadius: 10, padding: '10px 14px', fontSize: 13, margin: '10px 0' },
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
            <span>{cart?.itens?.length > 0 ? `${cart.itens.length} item(ns) no carrinho` : 'Carrinho vazio'}</span>
          </div>
          <span>{cart?.itens?.length > 0 ? `${formatCurrency(cartTotal)} →` : 'Frete grátis acima de R$ 199'}</span>
        </div>
      </div>

      {/* HEADER */}
      <div style={S.header}>
        <div style={S.headerInner}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={S.logo} onClick={() => setView('loja')}>
              <span style={{ fontSize: 42, lineHeight: 1, flexShrink: 0 }}>🐾</span>
              <div>
                <div style={{ fontSize: 18, fontWeight: 800, color: '#1c1917', lineHeight: 1.1 }}>{storeDisplayName}</div>
                {(tenantContext?.cidade || tenantContext?.uf) && (
                  <div style={{ fontSize: 11, color: '#a8a29e', fontWeight: 400, marginTop: 1 }}>
                    📍 {tenantContext?.cidade || ''}{tenantContext?.uf ? ` - ${tenantContext.uf}` : ''}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Search (desktop) */}
          <div style={{ flex: 1, maxWidth: 440, display: isMobile ? 'none' : 'flex' }} className="eco-search-wrap">
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
            {/* Wishlist */}
            <button onClick={() => setView('conta')} style={S.headerWishBtn} title={`Lista de desejos${wishlist.length > 0 ? ` (${wishlist.length})` : ''}`}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill={wishlist.length > 0 ? '#f97316' : 'none'} stroke={wishlist.length > 0 ? '#f97316' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
            </button>
            {/* Login/Conta */}
            {customerDisplayName ? (
              <button onClick={() => setView('conta')} style={S.avatarBtn}>
                <span style={{ width: 22, height: 22, borderRadius: '50%', background: '#f97316', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800 }}>{customerDisplayName.charAt(0).toUpperCase()}</span>
                {customerDisplayName.split(' ')[0]}
              </button>
            ) : (
              <button onClick={() => setView('conta')} style={{ ...S.loginBtn, gap: 6, padding: isMobile ? '7px 10px' : '7px 16px' }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                {!isMobile && 'Entrar'}
              </button>
            )}
            {/* Carrinho */}
            <button onClick={() => setView('carrinho')} style={{ ...S.cartBtn, padding: isMobile ? '0 12px' : '0 18px' }}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
              {isMobile ? (cart?.itens?.length > 0 ? `(${cart.itens.length})` : '') : `Carrinho${cart?.itens?.length > 0 ? ` (${cart.itens.length})` : ''}`}
            </button>
          </div>
        </div>
      </div>

      {/* BANNER (só na aba loja) */}
      {view === 'loja' && (
        <div style={{ padding: '16px 20px 0', boxSizing: 'border-box' }}>
          <div style={{ ...S.bannerWrap, borderRadius: isMobile ? 12 : 16, maxWidth: 1280, margin: '0 auto', height: isMobile ? 180 : 260 }}>
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
        </div>
      )}

      {/* BARRA APP */}
      {view === 'loja' && !isMobile && (
        <div style={S.appBar}>
          <div style={S.appBarInner}>
            <span style={{ background: '#16a34a', borderRadius: 8, width: 28, height: 28, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>
            </span>
            Baixe nosso <strong>APP</strong> para notificações de pedidos, promoções e aviso de reposição de estoque.
          </div>
        </div>
      )}

      {/* NAV TABS */}
      <div style={{ ...S.navWrap, overflowX: isMobile ? 'auto' : 'visible' }}>
        <div style={S.navInner}>
          {[
            { id: 'loja', label: 'Loja', icon: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg> },
            { id: 'carrinho', label: cart?.itens?.length ? `Carrinho (${cart.itens.length})` : 'Carrinho', icon: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg> },
            { id: 'pedidos', label: 'Pedidos', icon: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg> },
            { id: 'conta', label: 'Conta', icon: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> },
          ].map(({ id, label, icon }) => (
            <button key={id} onClick={() => setView(id)} style={{ ...S.navTab(view === id), display: 'flex', alignItems: 'center', gap: 5 }}>
              {icon}
              {label}
            </button>
          ))}
        </div>
      </div>



      {!tenantRef && (
        <div style={{ background: '#fef2f2', color: '#991b1b', padding: '10px 20px', fontSize: 13, borderBottom: '1px solid #fecaca' }}>
          ⚠️ Use a URL no formato: /slug-da-loja
        </div>
      )}

      {/* ALERTAS */}
      {(error || success) && (
        <div style={{ padding: '0 20px' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto' }}>
            {error && <div style={S.alertError}>⚠️ {error}</div>}
            {success && <div style={S.alertSuccess}>✓ {success}</div>}
          </div>
        </div>
      )}

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
                      {tipoRetirada === 'proprio' && (
                        <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '10px 12px', background: isDrive ? '#fff7ed' : '#f8fafc', border: `1.5px solid ${isDrive ? '#f97316' : '#e5e7eb'}`, borderRadius: 10 }}>
                          <input type="checkbox" checked={isDrive} onChange={(e) => setIsDrive(e.target.checked)} style={{ width: 18, height: 18, cursor: 'pointer' }} />
                          <div>
                            <div style={{ fontWeight: 700, fontSize: 13, color: '#1a1a2e' }}>🚗 Quero usar o Drive</div>
                            <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>Avise pela loja quando chegar no estacionamento — sem sair do carro!</div>
                          </div>
                        </label>
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
                  const opcs = [{ key: 'pix', label: 'PIX', icon: '📱' }, { key: 'debito', label: 'Débito', icon: '💳' }, { key: 'credito', label: 'Crédito', icon: '💳' }];
                  const bandeiras = ['Visa', 'Mastercard', 'Elo', 'Outra'];
                  return (
                    <div style={{ display: 'grid', gap: 10 }}>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {opcs.map((o) => (
                          <label key={o.key} style={pagamentoTipo === o.key ? S.radioLabelActive : S.radioLabel}>
                            <input type="radio" name="pagamentoTipo" value={o.key} checked={pagamentoTipo === o.key} onChange={() => setPagamentoTipo(o.key)} style={{ display: 'none' }} />
                            {o.icon} {o.label}
                          </label>
                        ))}
                      </div>
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
                <div style={{ marginTop: 10, fontSize: 12, color: '#92400e', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8, padding: '8px 10px' }}>
                  O carrinho ainda nao e pedido. O pedido so sera liberado apos aprovacao do pagamento online.
                </div>
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
                {checkoutLoading ? 'Abrindo pagamento...' : 'Ir para pagamento'}
              </button>

              {!isProfileComplete && (
                <div style={{ fontSize: 12, color: '#b45309', background: '#fffbeb', borderRadius: 8, padding: '8px 10px', marginTop: 6 }}>
                  ⚠️ Complete seu cadastro (nome, telefone, CPF e endereço) na aba Conta para finalizar.
                </div>
              )}

              {checkoutResult?.pedido_id && (
                <div style={{ background: '#ecfdf5', border: '1.5px solid #6ee7b7', borderRadius: 12, padding: 14, marginTop: 8, display: 'grid', gap: 6 }}>
                  <div style={{ fontWeight: 700, color: '#065f46', fontSize: 14 }}>Pagamento em analise</div>
                  <div style={{ fontSize: 13, color: '#374151' }}>Número: <strong>{checkoutResult.pedido_id}</strong></div>
                  <div style={{ fontSize: 12, color: '#047857' }}>O pedido sera liberado para a loja apos aprovacao do pagamento.</div>
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

                    {order.is_drive && order.tipo_retirada === 'proprio' && (
                      <div style={{ background: order.drive_entregue_at ? '#f0fdf4' : order.drive_chegou_at ? '#fef9c3' : '#f0f9ff', border: `2px solid ${order.drive_entregue_at ? '#22c55e' : order.drive_chegou_at ? '#eab308' : '#3b82f6'}`, borderRadius: 10, padding: 12, marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
                        {order.drive_entregue_at ? (
                          <div style={{ color: '#15803d', fontWeight: 700, fontSize: 14 }}>✅ Entregue no Drive!</div>
                        ) : order.drive_chegou_at ? (
                          <>
                            <div style={{ color: '#854d0e', fontWeight: 700, fontSize: 13 }}>🚗 Chegada registrada — aguarde a equipe!</div>
                            <div style={{ color: '#78716c', fontSize: 11 }}>Registrado às {new Date(order.drive_chegou_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
                          </>
                        ) : (
                          <>
                            <div style={{ color: '#1d4ed8', fontWeight: 700, fontSize: 13 }}>🚗 Pedido com Drive</div>
                            <div style={{ color: '#6b7280', fontSize: 11, textAlign: 'center' }}>Quando chegar no estacionamento, clique no botão abaixo.</div>
                            <button
                              onClick={() => avisarCheguei(order.pedido_id)}
                              style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: 10, padding: '10px 24px', fontWeight: 700, fontSize: 14, cursor: 'pointer', marginTop: 2 }}
                            >
                              🚗 Cheguei! Estou no estacionamento
                            </button>
                          </>
                        )}
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
                    <input value={profileForm.telefone} onChange={(e) => setProfileForm((prev) => ({ ...prev, telefone: e.target.value }))} placeholder="Telefone *" style={S.formInput} required />
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
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 20 }}>
              {/* Cadastro */}
              <div style={S.accountCard}>
                <div style={{ fontWeight: 800, fontSize: 20, color: '#1c1917', marginBottom: 14 }}>Criar conta</div>
                <form onSubmit={handleRegister} autoComplete="off" style={{ display: 'grid', gap: 10 }}>
                  <input name="ecommerce_register_nome" autoComplete="off" value={registerForm.nome} onChange={(e) => setRegisterForm((prev) => ({ ...prev, nome: e.target.value }))} placeholder="Nome completo" style={S.formInput} />
                  <input name="ecommerce_register_cpf" autoComplete="off" value={registerForm.cpf} onChange={(e) => setRegisterForm((prev) => ({ ...prev, cpf: e.target.value }))} placeholder="CPF *  (000.000.000-00)" inputMode="numeric" style={S.formInput} required />
                  <input name="ecommerce_register_telefone" autoComplete="off" value={registerForm.telefone} onChange={(e) => setRegisterForm((prev) => ({ ...prev, telefone: e.target.value }))} placeholder="Telefone/WhatsApp *" inputMode="tel" style={S.formInput} required />
                  <input name="ecommerce_register_email" autoComplete="off" value={registerForm.email} onChange={(e) => setRegisterForm((prev) => ({ ...prev, email: e.target.value }))} placeholder="Email" type="email" style={S.formInput} />
                  <div style={{ position: 'relative' }}>
                    <input name="ecommerce_register_password" autoComplete="new-password" value={registerForm.password} onChange={(e) => setRegisterForm((prev) => ({ ...prev, password: e.target.value }))} placeholder="Senha (minimo 8 caracteres)" type={showRegisterPassword ? 'text' : 'password'} style={{ ...S.formInput, paddingRight: 80, width: '100%', boxSizing: 'border-box' }} />
                    <button type="button" onClick={() => setShowRegisterPassword((prev) => !prev)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: '#6b7280' }}>
                      {showRegisterPassword ? 'Ocultar' : '👁 Ver'}
                    </button>
                  </div>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12, color: '#57534e', lineHeight: 1.45 }}>
                    <input type="checkbox" checked={registerForm.accepted_terms} onChange={(e) => setRegisterForm((prev) => ({ ...prev, accepted_terms: e.target.checked }))} style={{ marginTop: 2 }} />
                    <span>Li e aceito os <a href="/termos" target="_blank" rel="noreferrer" style={{ color: '#7c3aed', fontWeight: 700 }}>Termos de Uso</a>.</span>
                  </label>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12, color: '#57534e', lineHeight: 1.45 }}>
                    <input type="checkbox" checked={registerForm.accepted_privacy} onChange={(e) => setRegisterForm((prev) => ({ ...prev, accepted_privacy: e.target.checked }))} style={{ marginTop: 2 }} />
                    <span>Li e aceito a <a href="/privacidade" target="_blank" rel="noreferrer" style={{ color: '#7c3aed', fontWeight: 700 }}>Politica de Privacidade</a>.</span>
                  </label>
                  <button type="submit" disabled={authLoading} style={S.saveBtn}>{authLoading ? 'Criando...' : 'Criar minha conta'}</button>
                </form>
              </div>

              {/* Login / Recuperação */}
              <div style={S.accountCard}>
                <div style={{ fontWeight: 800, fontSize: 20, color: '#1c1917', marginBottom: 10 }}>
                  {passwordRecoveryMode ? 'Recuperar senha' : 'Entrar'}
                </div>
                <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 14 }}>
                  {passwordRecoveryMode
                    ? (recoveryStep === 'request'
                        ? 'Informe o e-mail da conta e enviaremos as instruções.'
                        : recoveryTokenFromLink
                          ? 'Link seguro carregado. Escolha uma nova senha.'
                          : 'Digite o codigo recebido e escolha uma nova senha.')
                    : 'Acesse sua conta para acompanhar pedidos e finalizar a compra mais rápido.'}
                </div>

                {passwordRecoveryMode ? (
                  <form
                    onSubmit={recoveryStep === 'request' ? handlePasswordRecoveryRequest : handlePasswordRecoveryReset}
                    autoComplete="off"
                    style={{ display: 'grid', gap: 10 }}
                  >
                    <input
                      name="ecommerce_recovery_email"
                      autoComplete="off"
                      value={recoveryForm.email}
                      onChange={(e) => setRecoveryForm((prev) => ({ ...prev, email: e.target.value }))}
                      placeholder="Email"
                      type="email"
                      style={S.formInput}
                    />

                    {recoveryStep === 'reset' && (
                      <>
                        {recoveryTokenFromLink ? (
                          <div style={{ border: '1px solid #ddd6fe', background: '#f5f3ff', color: '#5b21b6', borderRadius: 10, padding: '10px 12px', fontSize: 13, fontWeight: 600 }}>
                            Link de recuperacao carregado. Basta cadastrar a nova senha.
                          </div>
                        ) : (
                          <input
                            name="ecommerce_recovery_token"
                            autoComplete="off"
                            inputMode="numeric"
                            value={recoveryForm.token}
                            onChange={(e) => setRecoveryForm((prev) => ({ ...prev, token: e.target.value }))}
                            placeholder="Codigo de recuperacao"
                            type="text"
                            style={S.formInput}
                          />
                        )}
                        <div style={{ position: 'relative' }}>
                          <input
                            name="ecommerce_recovery_password"
                            autoComplete="new-password"
                            value={recoveryForm.novaSenha}
                            onChange={(e) => setRecoveryForm((prev) => ({ ...prev, novaSenha: e.target.value }))}
                            placeholder="Nova senha"
                            type={showRecoveryPassword ? 'text' : 'password'}
                            style={{ ...S.formInput, paddingRight: 80, width: '100%', boxSizing: 'border-box' }}
                          />
                          <button
                            type="button"
                            onClick={() => setShowRecoveryPassword((prev) => !prev)}
                            style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: '#6b7280' }}
                          >
                            {showRecoveryPassword ? 'Ocultar' : '👁 Ver'}
                          </button>
                        </div>
                        <div style={{ position: 'relative' }}>
                          <input
                            name="ecommerce_recovery_password_confirm"
                            autoComplete="new-password"
                            value={recoveryForm.confirmarSenha}
                            onChange={(e) => setRecoveryForm((prev) => ({ ...prev, confirmarSenha: e.target.value }))}
                            placeholder="Confirmar nova senha"
                            type={showRecoveryConfirmPassword ? 'text' : 'password'}
                            style={{ ...S.formInput, paddingRight: 80, width: '100%', boxSizing: 'border-box' }}
                          />
                          <button
                            type="button"
                            onClick={() => setShowRecoveryConfirmPassword((prev) => !prev)}
                            style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: '#6b7280' }}
                          >
                            {showRecoveryConfirmPassword ? 'Ocultar' : '👁 Ver'}
                          </button>
                        </div>
                      </>
                    )}

                    <button type="submit" disabled={recoveryLoading} style={S.saveBtn}>
                      {recoveryLoading
                        ? 'Processando...'
                        : recoveryStep === 'request'
                          ? 'Enviar instruções'
                          : 'Salvar nova senha'}
                    </button>

                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {recoveryStep === 'request' ? (
                        <button
                          type="button"
                          onClick={() => {
                            setRecoveryStep('reset');
                            setRecoveryTokenFromLink(false);
                          }}
                          style={{ background: '#fff', border: '1.5px solid #d1d5db', color: '#374151', borderRadius: 10, padding: '10px 16px', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}
                        >
                          Ja tenho o codigo
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setRecoveryStep('request');
                            setRecoveryTokenFromLink(false);
                            setError('');
                            setSuccess('');
                          }}
                          style={{ background: '#fff', border: '1.5px solid #d1d5db', color: '#374151', borderRadius: 10, padding: '10px 16px', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}
                        >
                          Solicitar novo link
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={closePasswordRecovery}
                        style={{ background: 'transparent', border: 'none', color: '#2563eb', fontWeight: 700, fontSize: 13, cursor: 'pointer', padding: '10px 0' }}
                      >
                        Voltar para login
                      </button>
                    </div>
                  </form>
                ) : (
                  <form onSubmit={handleLogin} autoComplete="off" style={{ display: 'grid', gap: 10 }}>
                    <input name="ecommerce_login_email" autoComplete="off" value={loginForm.email} onChange={(e) => setLoginForm((prev) => ({ ...prev, email: e.target.value }))} placeholder="Email" type="email" style={S.formInput} />
                    <div style={{ position: 'relative' }}>
                      <input name="ecommerce_login_password" autoComplete="new-password" value={loginForm.password} onChange={(e) => setLoginForm((prev) => ({ ...prev, password: e.target.value }))} placeholder="Senha" type={showLoginPassword ? 'text' : 'password'} style={{ ...S.formInput, paddingRight: 80, width: '100%', boxSizing: 'border-box' }} />
                      <button type="button" onClick={() => setShowLoginPassword((prev) => !prev)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: '#6b7280' }}>
                        {showLoginPassword ? 'Ocultar' : '👁 Ver'}
                      </button>
                    </div>
                    <button type="submit" disabled={authLoading} style={S.saveBtn}>{authLoading ? 'Entrando...' : 'Entrar'}</button>
                    <button
                      type="button"
                      onClick={() => openPasswordRecovery('request')}
                      style={{ background: 'transparent', border: 'none', color: '#2563eb', fontWeight: 700, fontSize: 13, cursor: 'pointer', justifySelf: 'start', padding: 0 }}
                    >
                      Esqueci minha senha
                    </button>
                  </form>
                )}
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
