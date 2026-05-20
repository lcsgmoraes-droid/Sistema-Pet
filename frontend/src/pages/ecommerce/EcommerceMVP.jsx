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
import useEcommerceCart from './useEcommerceCart';
import useEcommerceCatalog from './useEcommerceCatalog';
import useEcommerceCheckout from './useEcommerceCheckout';
import useEcommerceCustomer from './useEcommerceCustomer';
import useEcommerceEngagement from './useEcommerceEngagement';
import useEcommerceOrders from './useEcommerceOrders';
import useEcommerceProductModal from './useEcommerceProductModal';
import {
  trackPageView,
  trackViewCart,
} from '../../services/analytics';
import {
  STORAGE_TOKEN_KEY,
  buildActiveBanners,
  extractApiErrorMessage,
  isProductOutOfStock,
  normalizeProductPayload,
  resolveStoreDisplayName,
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
  const [customerToken, setCustomerToken] = useState(localStorage.getItem(STORAGE_TOKEN_KEY) || '');

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [tenantContext, setTenantContext] = useState(null);

  // Banners: usa URLs do tenant se configuradas, senão exibe os padrões
  const activeBanners = useMemo(() => {
    return buildActiveBanners(tenantContext);
  }, [tenantContext]);

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

  const storeDisplayName = useMemo(() => {
    return resolveStoreDisplayName({ tenantContext, storefrontRef });
  }, [tenantContext, storefrontRef]);

  const {
    cart,
    cartLoading,
    cartTotal,
    addToCart,
    clearCart,
    loadCart,
    restoreGuestCart,
    syncGuestCartToServer,
    updateCartItem,
  } = useEcommerceCart({
    authHeaders,
    customerToken,
    productMap,
    onError: setError,
    onSuccess: setSuccess,
  });

  const {
    authLoading,
    clearCustomerSession,
    closePasswordRecovery,
    customer,
    customerDisplayName,
    handleDeliveryCepBlur,
    handleLogin,
    handlePasswordRecoveryRequest,
    handlePasswordRecoveryReset,
    handleProfileCepBlur,
    handleRegister,
    isProfileComplete,
    loginForm,
    openPasswordRecovery,
    passwordRecoveryMode,
    profileForm,
    profileSaving,
    recoveryForm,
    recoveryLoading,
    recoveryStep,
    recoveryTokenFromLink,
    registerForm,
    saveProfile,
    setLoginForm,
    setProfileForm,
    setRecoveryForm,
    setRecoveryStep,
    setRecoveryTokenFromLink,
    setRegisterForm,
    setShowLoginPassword,
    setShowRecoveryConfirmPassword,
    setShowRecoveryPassword,
    setShowRegisterPassword,
    showLoginPassword,
    showRecoveryConfirmPassword,
    showRecoveryPassword,
    showRegisterPassword,
  } = useEcommerceCustomer({
    authHeaders,
    customerToken,
    loadCart,
    location,
    navigate,
    restoreGuestCart,
    setCustomerToken,
    setView,
    syncGuestCartToServer,
    tenantContext,
    tenantHeaders,
    onError: setError,
    onSuccess: setSuccess,
  });

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

  const {
    addressFields,
    checkoutLoading,
    checkoutResumo,
    checkoutResult,
    cidadeDestino,
    cupom,
    cupomResult,
    deliveryMode,
    isDrive,
    pagamentoBandeira,
    pagamentoParcelas,
    pagamentoTipo,
    tipoRetirada,
    applyCupom,
    calcularResumoCheckout,
    finalizarCheckout,
    handleCheckoutCepBlur,
    handleCheckoutFromLoja,
    resetCheckoutStatus,
    setAddressFields,
    setCidadeDestino,
    setCupom,
    setDeliveryMode,
    setIsDrive,
    setPagamentoBandeira,
    setPagamentoParcelas,
    setPagamentoTipo,
    setTipoRetirada,
  } = useEcommerceCheckout({
    authHeaders,
    cart,
    clearCart,
    customer,
    customerToken,
    isProfileComplete,
    recordOrderId,
    setView,
    tenantContext,
    onError: setError,
    onSuccess: setSuccess,
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
    const total = activeBanners.length;
    const timer = setInterval(() => setBannerSlide((prev) => (prev + 1) % total), 4000);
    return () => clearInterval(timer);
  }, [activeBanners.length]);

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

  function logoutCustomer() {
    clearCustomerSession();
    clearCart();
    resetCheckoutStatus();
    setSuccess('Sess\u00e3o encerrada.');
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
