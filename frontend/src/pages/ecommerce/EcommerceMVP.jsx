import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import ecommerceApi from '../../services/ecommerceApi';
import { api } from '../../services/api';
import EcommerceAccountPage from './EcommerceAccountPage';
import { EcommerceCartPage } from './EcommerceCartPanels';
import EcommerceCheckoutPage from './EcommerceCheckoutPage';
import EcommerceFooter from './EcommerceFooter';
import EcommerceNotifyMeModal from './EcommerceNotifyMeModal';
import EcommerceOrdersPage from './EcommerceOrdersPage';
import EcommerceProductDetailModal from './EcommerceProductDetailModal';
import EcommerceStorePage from './EcommerceStorePage';
import EcommerceStorefrontChrome from './EcommerceStorefrontChrome';
import useEcommerceCatalog from './useEcommerceCatalog';
import useEcommerceEngagement from './useEcommerceEngagement';
import useEcommerceOrders from './useEcommerceOrders';
import useEcommerceProductModal from './useEcommerceProductModal';
import {
  trackPageView,
  trackAddToCart,
  trackBeginCheckout,
  trackPurchase,
  trackViewCart,
} from '../../services/analytics';
import {
  EMPTY_CART,
  STORAGE_ADDRESS_KEY,
  STORAGE_GUEST_CART_KEY,
  STORAGE_TOKEN_KEY,
  buildActiveBanners,
  buildCustomerAddressFields,
  buildCustomerProfileForm,
  buildAddressText,
  buildIdempotencyKey,
  extractApiErrorMessage,
  fetchAddressByCep,
  getGuestCart,
  getStoredAddressFields,
  isCustomerProfileComplete,
  isProductOutOfStock,
  normalizeProductPayload,
  recalculateGuestCart,
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
  const {
    products,
    setProducts,
    search,
    setSearch,
    categoria,
    setCategoria,
    somenteComEstoque,
    setSomenteComEstoque,
    somenteComImagem,
    setSomenteComImagem,
    ordenacaoCatalogo,
    setOrdenacaoCatalogo,
    categorias,
    catalogMetrics,
    filteredProducts,
    productMap,
    clearCatalogFilters,
  } = useEcommerceCatalog();
  const {
    selectedProduct,
    activeProductImage,
    setActiveProductImage,
    openProductDetails,
    closeProductModal,
  } = useEcommerceProductModal({ products, location, navigate });
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

  const storefrontRef = tenantContext?.ecommerce_slug || tenantRef || '';
  const customerDisplayName = customer?.nome || customer?.email || '';

  const storeDisplayName = useMemo(() => {
    return resolveStoreDisplayName({ tenantContext, storefrontRef });
  }, [tenantContext, storefrontRef]);

  const {
    wishlist,
    notifyRequests,
    notifyMeModal,
    setNotifyMeModal,
    toggleWishlist,
    registerNotifyMe,
    submitNotifyMe,
  } = useEcommerceEngagement({
    customer,
    loginEmail: loginForm.email,
    registerEmail: registerForm.email,
    storefrontRef,
    tenantContext,
    tenantRef,
    onError: setError,
    onSuccess: setSuccess,
  });

  const {
    ordersDetailed,
    ordersLoading,
    loadOrdersDetailed,
    avisarCheguei,
    recordOrderId,
  } = useEcommerceOrders({
    authHeaders,
    customerToken,
    view,
    onError: setError,
  });

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
        await recordOrderId(result.pedido_id);
      }

      setSuccess('Pagamento enviado para analise. O pedido sera liberado apos aprovacao.');
      setView('pedidos');
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Erro ao finalizar checkout'));
    } finally {
      setCheckoutLoading(false);
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
      <EcommerceStorefrontChrome
        activeBanners={activeBanners}
        bannerSlide={bannerSlide}
        cart={cart}
        cartTotal={cartTotal}
        customerDisplayName={customerDisplayName}
        isMobile={isMobile}
        search={search}
        storeDisplayName={storeDisplayName}
        styles={S}
        tenantContext={tenantContext}
        view={view}
        wishlist={wishlist}
        onBannerSlideChange={setBannerSlide}
        onNavigate={setView}
        onSearchChange={setSearch}
      />

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
        <EcommerceStorePage
          cart={cart}
          cartTotal={cartTotal}
          catalogMetrics={catalogMetrics}
          categories={categorias}
          category={categoria}
          customerToken={customerToken}
          filteredProducts={filteredProducts}
          hoveredCard={hoveredCard}
          isMobile={isMobile}
          loading={loading}
          order={ordenacaoCatalogo}
          productMap={productMap}
          search={search}
          showOnlyInStock={somenteComEstoque}
          showOnlyWithImage={somenteComImagem}
          styles={S}
          wishlist={wishlist}
          onAddToCart={addToCart}
          onCategoryChange={setCategoria}
          onCheckout={handleCheckoutFromLoja}
          onClearFilters={clearCatalogFilters}
          onHoverProduct={setHoveredCard}
          onImageFilterChange={() => setSomenteComImagem((value) => !value)}
          onNotifyMe={registerNotifyMe}
          onOpenProduct={openProductDetails}
          onOrderChange={setOrdenacaoCatalogo}
          onRefresh={loadProducts}
          onSearchChange={setSearch}
          onStockFilterChange={() => setSomenteComEstoque((value) => !value)}
          onToggleWishlist={toggleWishlist}
          onViewCart={() => setView('carrinho')}
        />
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
          checkoutResumo={checkoutResumo}
          checkoutResult={checkoutResult}
          cidadeDestino={cidadeDestino}
          deliveryMode={deliveryMode}
          isDrive={isDrive}
          isProfileComplete={isProfileComplete}
          pagamentoBandeira={pagamentoBandeira}
          pagamentoParcelas={pagamentoParcelas}
          pagamentoTipo={pagamentoTipo}
          setAddressFields={setAddressFields}
          styles={S}
          tenantContext={tenantContext}
          tipoRetirada={tipoRetirada}
          onCalculateSummary={calcularResumoCheckout}
          onCheckoutCepBlur={handleCheckoutCepBlur}
          onCidadeDestinoChange={setCidadeDestino}
          onDeliveryModeChange={setDeliveryMode}
          onFinalizeCheckout={finalizarCheckout}
          onIsDriveChange={setIsDrive}
          onPagamentoBandeiraChange={setPagamentoBandeira}
          onPagamentoParcelasChange={setPagamentoParcelas}
          onPagamentoTipoChange={setPagamentoTipo}
          onTipoRetiradaChange={setTipoRetirada}
        />
      )}

      {view === 'pedidos' && (
        <EcommerceOrdersPage
          orders={ordersDetailed}
          ordersLoading={ordersLoading}
          styles={S}
          onContinueShopping={() => setView('loja')}
          onDriveArrived={avisarCheguei}
          onReload={loadOrdersDetailed}
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
          setLoginForm={setLoginForm}
          setProfileForm={setProfileForm}
          setRecoveryForm={setRecoveryForm}
          setRegisterForm={setRegisterForm}
          showLoginPassword={showLoginPassword}
          showRecoveryConfirmPassword={showRecoveryConfirmPassword}
          showRecoveryPassword={showRecoveryPassword}
          showRegisterPassword={showRegisterPassword}
          styles={S}
          wishlistCount={wishlist.length}
          onClosePasswordRecovery={closePasswordRecovery}
          onDeliveryCepBlur={handleDeliveryCepBlur}
          onLogin={handleLogin}
          onLogout={logoutCustomer}
          onOpenPasswordRecovery={openPasswordRecovery}
          onPasswordRecoveryRequest={handlePasswordRecoveryRequest}
          onPasswordRecoveryReset={handlePasswordRecoveryReset}
          onProfileCepBlur={handleProfileCepBlur}
          onRegister={handleRegister}
          onSaveProfile={saveProfile}
          onSwitchRecoveryToRequest={() => {
            setRecoveryStep('request');
            setRecoveryTokenFromLink(false);
            setError('');
            setSuccess('');
          }}
          onSwitchRecoveryToReset={() => {
            setRecoveryStep('reset');
            setRecoveryTokenFromLink(false);
          }}
          onToggleLoginPassword={() => setShowLoginPassword((prev) => !prev)}
          onToggleRecoveryConfirmPassword={() => setShowRecoveryConfirmPassword((prev) => !prev)}
          onToggleRecoveryPassword={() => setShowRecoveryPassword((prev) => !prev)}
          onToggleRegisterPassword={() => setShowRegisterPassword((prev) => !prev)}
        />
      )}

      <EcommerceNotifyMeModal
        modal={notifyMeModal}
        styles={S}
        onClose={() => setNotifyMeModal({ open: false, product: null, email: '', loading: false })}
        onEmailChange={(email) => setNotifyMeModal((prev) => ({ ...prev, email }))}
        onSubmit={submitNotifyMe}
      />

      <EcommerceFooter tenantContext={tenantContext} styles={S} onNavigate={setView} />
    </div>
  );
}
